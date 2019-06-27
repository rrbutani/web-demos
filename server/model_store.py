import time
import os
from typing import List, Tuple, Union, Optional

import numpy as np
import tensorflow as tf

from server.types.metrics import Metrics
from server.debug import dprint, if_debug

dprint(f"TF Version: {tf.__version__}")
# tf.enable_eager_execution() # TODO
# if_debug(lambda: tf.logging.set_verbosity(tf.logging.DEBUG)) # TODO

Interpreter = tf.lite.Interpreter

Error = str
Tensor = np.ndarray
Handle = int


class ModelRegisterError(Exception):
    ...


class ModelLoadError(Exception):
    ...


class InvalidHandleError(Exception):
    ...


class TensorTypeError(Exception):
    ...


# Can't raise exceptions in lambdas!
def raise_err(err):
    raise err


# TODO: spin off into an error module/file/thing
def equal_or_error(expected, actual, msg, ex):
    if expected != actual:
        raise ex(f"{msg}; Expected: `{expected}`, Got: `{actual}`")


class LocalModel:
    def __init__(self, model: Optional[str] = None, path: Optional[str] = None):
        """
        :raises ModelRegisterError: When given obviously incorrect models.
        """
        # String with the model's contents; used to set model_content in the
        # TFLite Interpreter's constructor.
        self.model: Optional[str] = model

        # Path for models that exist on disk. Models specified by path will be
        # loaded if self.model isn't set.
        self.path: Optional[str] = path

        from_str, from_file = self.model is not None, self.path is not None

        # Validate the options we were passed:
        {  # (this is supposed to be a switch case, I'm sorry)
            (True, True): self._check_str_model,
            (True, False): self._check_str_model,
            (False, True): self._check_file_model,
            (False, False): lambda: raise_err(
                ModelRegisterError("No Model specified!")
            ),
        }[(from_str, from_file)]()

        self.interp: Optional[Interpreter] = None
        self.def_shape: Optional[List[int]] = None
        self.def_rank: Optional[int] = None

    def _check_str_model(self):
        """
        :raises ModelRegisterError: On empty string models.
        """
        if self.model == "":
            raise ModelRegisterError("Provided model was empty.")

    def _check_file_model(self):
        """
        :raises ModelRegisterError: On obviously incorrect/invalid file models.
        """
        if not os.path.exists(self.path):
            raise ModelRegisterError(f"Model path ({self.path}) doesn't exist.")
        if not os.path.isfile(self.path):
            raise ModelRegisterError(f"Model path ({self.path}) isn't a file.")
        if not os.path.splitext(self.path)[1] == ".tflite":
            raise ModelRegisterError(
                f"File ({self.path}) doesn't seem to be a TFLite model."
            )

    def _prepare_interpreter(self):
        """
        :raises ModelLoadError: When the given model cannot be loaded.
        """
        # If we have yet to create an interpreter for this model..
        if self.interp is None:
            # ..do so:
            try:
                # From a string, if we've got it:
                if self.model is not None:
                    self.interp = Interpreter(model_content=self.model)
                # If not, try a file if we've got one:
                elif self.path is not None:
                    self.interp = Interpreter(model_path=self.path)
                # Failing that, bail:
                else:
                    raise ModelLoadError(
                        "Internal Error! Got a model without a path or"
                        " data (this isn't supposed to be possible)."
                    )
            except RuntimeError as e:
                raise ModelLoadError(
                    f"Failed to load the model. Got: `{e}`."
                    f"(model = `{self.model}`, path = `{self.path}`)"
                )

            # Finally, some more initialization:
            self.def_shape = tuple(self.interp.get_input_details()[0]["shape"])
            self.def_rank = len(self.def_shape)

            self.interp.allocate_tensors()

            dprint("Loaded new model.")

    def _resize_internal(self, shape: Tuple[int]):
        """
        :raises RuntimeError: When the interpreter is unable to resize the tensors.
        """
        assert self.interp is not None

        input_details = self.interp.get_input_details()[0]
        current_shape = tuple(input_details["shape"])
        input_index = input_details["index"]

        if current_shape == shape:
            return

        dprint(f"Attempting to resize `{current_shape}` to `{shape}`..")
        self.interp.resize_tensor_input(input_index, shape)
        self.interp.allocate_tensors()
        dprint("Success!")

    def _resize(self, shape: Tuple[int], backup: Optional[Tuple[int]] = None) -> bool:
        """
        :raises RuntimeError: When the interpreter is unable to resize the tensors.
        :raises TensorTypeError: On error when bail is set to True.

        Returns True if the backup shape was used (i.e. used to set the shape).
        """
        assert self.interp is not None

        def throw(shape, e):
            raise TensorTypeError(
                "Unable to resize the model's input tensor to"
                f" match the given tensor. Attempted `{shape}`"
                f" last and got `{e}`."
            )

        # Try the first shape:
        try:
            self._resize_internal(shape)
            return False
        except RuntimeError as e:
            if backup is None:
                throw(shape, e)

        # Try the second shape:
        try:
            self._resize_internal(backup)
            return True
        except RuntimeError as e:
            throw(backup, e)

    def _check_tensor(self, tensor: Tensor) -> Tuple[Tensor, int]:
        """
        :raises TensorTypeError: When the given tensor cannot be used.
        """
        assert self.interp is not None

        input_details = self.interp.get_input_details()[0]

        # Check the tensor's data type:
        equal_or_error(
            input_details["dtype"],
            tensor.dtype,
            "Data types don't match",
            TensorTypeError,
        )

        # And its shape:

        # Shape checking isn't as straightforward as data type checking, because
        # the input tensor's shape will differ if it's a batch.
        manual_batch_size = 0
        shape, rank = tensor.shape, len(tensor.shape)

        # If we've got an extra dimension (and if the other dimensions match our
        # original shape), we'll try to load the input tensor as a batch:
        if rank == self.def_rank + 1 and shape[1:] == self.def_shape:
            # Try native batches and manual batches as a backup:
            if self._resize(shape, shape[1:]):
                # If we're going with manual batches:
                manual_batch_size = shape[0]

        # If we've got the same number of dimensions but a different number of
        # the first dimension _and_ the first dimension is expected to be 1,
        # we'll also try to use the input tensor as a batch:
        elif (
            rank == self.def_rank
            and shape[1:] == self.def_shape[1:]
            and shape[0] != self.def_shape[0]
            and self.def_shape[0] == 1
        ):
            # Native batches or manual batches if that doesn't work:
            if self._resize(shape, self.def_shape):
                # If manual batches:
                manual_batch_size = shape[0]
                tensor = np.reshape(tensor, [shape[0]] + self.def_shape)

        # If our model is expecting a batch of one, but the input tensor is
        # singular, wrap the input tensor to make it a batch of one:
        elif rank == self.def_rank - 1 and self.def_shape[0] == 1 and shape == self.def_shape[1:]:
            self._resize(self.def_shape)
            tensor = np.reshape(tensor, self.def_shape)

        # If the input tensor matches the shape we're looking for, use it as is:
        elif shape == self.def_shape:
            self._resize(shape)

        # Otherwise, we can't use the input tensor:
        else:
            def_shape = list(self.def_shape)
            shapes = [def_shape, ["X"] + def_shape]
            if def_shape[0] == 1:
                exp = (
                    f"`{shapes[0]}`, `{shapes[1]}` (batch), "
                    f"`{['X'] + def_shape[1:]}` (batch), or "
                    f"`{def_shape[1:]}` (singular)"
                )
            else:
                exp = f"`{shapes[0]}` or `{shapes[1]}` (batch)"

            raise TensorTypeError(
                f"Tensor Shape Mismatch; Expected {exp}, Got: " f"`{list(shape)}`"
            )

        # Finally, if we're not doing manual batching, wrap the tensor in a list
        # so that we can pretend we're making a batch of size 1:
        if manual_batch_size == 0:
            dprint("Pseudo manual batch")
            tensor = [tensor]
            manual_batch_size = 1
        else:
            dprint(f"Manual batch of size {manual_batch_size}")

        return tensor, manual_batch_size

    def _run_batch(self, tensor: Tensor, batch_size: int) -> Tuple[Tensor, Metrics]:
        assert self.interp is not None

        input_idx = self.interp.get_input_details()[0]["index"]
        output_idx = self.interp.get_output_details()[0]["index"]

        output, exec_time = None, 0

        for i in range(batch_size):
            self.interp.set_tensor(input_idx, tensor[i])

            begin = time.clock()
            self.interp.invoke()
            exec_time += time.clock() - begin

            output_part = self.interp.get_tensor(output_idx)
            if output is None:
                output = output_part
            else:
                output = np.append(output, output_part, axis=0)

        metrics = Metrics().time_to_execute(exec_time * (10 ** 6))  # in microseconds
        # .trace("") # TODO!!

        return output, metrics

    def predict(self, tensor: Optional[Tensor]) -> Tuple[Tensor, Metrics]:
        """
        :raises TensorTypeError: When the given tensor doesn't match the model.
        :raises ModelLoadError: If the given model cannot be loaded.
        """

        # Load the model if it's not already loaded:
        self._prepare_interpreter()

        # Check the input tensor:
        if tensor is None:
            raise TensorTypeError("Got an empty Tensor.")

        tensor, manual_batch_size = self._check_tensor(tensor)

        # And finally, try to run inference:
        try:
            return self._run_batch(tensor, manual_batch_size)
        except Exception as e:
            raise Exception(
                f"Encountered an error while trying to run inference: `{e}`."
            )


class ModelStore:
    def __init__(self):
        self.models: List[LocalModel] = []

        # TODO: remove
        # For now, let's load mnist-lstm in as model 0:
        assert 0 == self._load_from_file("models/mnist-lstm.tflite")
        # And mobilenet_float_v1_1.0_244 as model 1:
        assert 1 == self._load_from_file("models/mobilenet_float_v1_1.0_244.tflite")
        dprint("loaded built-in models!!")

    def load(self, model: str) -> Handle:
        """
        :raises ModelRegisterError: When given an obviously incorrect model.
        """
        self.models.append(LocalModel(model=model))

        return len(self.models) - 1

    def _load_from_file(self, path: str) -> Handle:
        """
        :raises ModelRegisterError: When given an obviously incorrect model.
        """
        self.models.append(LocalModel(path=path))

        return len(self.models) - 1

    def get(self, handle: Handle) -> LocalModel:
        """
        :raises InvalidHandleError: When asked for a handle that doesn't exist.
        """
        if handle >= len(self.models):
            raise InvalidHandleError(
                f"Handle with id {handle} does not exist."
                f" {len(self.models)} handles are "
                "currently registered."
            )

        return self.models[handle]
