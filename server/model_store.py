import os
import time
from typing import Any, Callable, Iterable, List
from typing import NoReturn as Never
from typing import Optional, Tuple, TypeVar, Union, cast

import numpy as np
import tensorflow as tf

from .debug import dprint, if_debug
from .types import MODEL_DIR
from .types.metrics import Metrics

dprint(f"TF Version: {tf.__version__}")
tf.compat.v1.enable_eager_execution()
_: None = if_debug(
    lambda: tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.DEBUG)
)

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
def raise_err(err: Exception) -> Never:
    raise err


T = TypeVar("T")

# TODO: spin off into an error module/file/thing
def equal_or_error(expected: T, actual: T, msg: str, ex: Callable[[str], Any]) -> None:
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
        # (this is supposed to be a switch case, I'm sorry)
        {  # type: ignore
            (True, True): self._check_str_model,
            (True, False): self._check_str_model,
            (False, True): self._check_file_model,
            (False, False): lambda: raise_err(
                ModelRegisterError("No Model specified!")
            ),
        }[(from_str, from_file)]()

        self.interp: Optional[tf.lite.Interpreter] = None
        self.def_shape: Optional[Tuple[int, ...]] = None
        self.def_rank: Optional[int] = None

    def _check_str_model(self) -> None:
        """
        :raises ModelRegisterError: On empty string models.
        """
        assert self.model is not None

        if self.model == "":
            raise ModelRegisterError("Provided model was empty.")

    def _check_file_model(self) -> None:
        """
        :raises ModelRegisterError: On obviously incorrect/invalid file models.
        """
        assert self.path is not None

        if not os.path.exists(self.path):
            raise ModelRegisterError(f"Model path ({self.path}) doesn't exist.")
        if not os.path.isfile(self.path):
            raise ModelRegisterError(f"Model path ({self.path}) isn't a file.")
        if not os.path.splitext(self.path)[1] == ".tflite":
            raise ModelRegisterError(
                f"File ({self.path}) doesn't seem to be a TFLite model."
            )

    def _prepare_interpreter(self) -> None:
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

    def _resize_internal(self, shape: Tuple[int, ...]) -> None:
        """
        :raises RuntimeError: When the interpreter is unable to resize the tensors.
        """
        assert self.interp is not None

        input_details = self.interp.get_input_details()[0]
        current_shape = tuple(input_details["shape"])
        input_index = input_details["index"]

        if current_shape != shape:
            dprint(f"Attempting to resize `{current_shape}` to `{shape}`..")
            self.interp.resize_tensor_input(input_index, shape)
            self.interp.allocate_tensors()
            dprint("Success!")

    def _resize(
        self, shape: Tuple[int, ...], backup: Optional[Tuple[int, ...]] = None
    ) -> bool:
        """
        :raises RuntimeError: When the interpreter is unable to resize the tensors.
        :raises TensorTypeError: On error when bail is set to True.

        Returns True if the backup shape was used (i.e. used to set the shape).
        """
        assert self.interp is not None

        def throw(shape: Iterable[int], e: Exception) -> Never:
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

        dtype = self.interp.get_input_details()[0]["dtype"]

        # Handle data types that aren't representable on the TFJS side:
        if (
            dtype == np.uint8
            or dtype == np.int8
            or dtype == np.int16
            or dtype == np.int64
        ) and tensor.dtype == np.int32:
            dprint(f"Warning: Casting tensor elements from {tensor.dtype} to {dtype}!")
            tensor = tensor.astype(dtype)

        # Check the tensor's data type:
        equal_or_error(dtype, tensor.dtype, "Data types don't match", TensorTypeError)

        # And its shape:

        # Shape checking isn't as straightforward as data type checking, because
        # the input tensor's shape will differ if it's a batch.
        manual_batch_size = 0
        shape, rank = tensor.shape, len(tensor.shape)

        # Because of where this is called, this _must_ be true but mypy doesn't
        # yet know this.
        assert self.def_shape is not None and self.def_rank is not None

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
                tensor = np.reshape(tensor, (shape[0],) + self.def_shape)

        # If our model is expecting a batch of one, but the input tensor is
        # singular, wrap the input tensor to make it a batch of one:
        elif (
            rank == self.def_rank - 1
            and self.def_shape[0] == 1
            and shape == self.def_shape[1:]
        ):
            self._resize(self.def_shape)
            tensor = np.reshape(tensor, self.def_shape)

        # If the input tensor matches the shape we're looking for, use it as is:
        elif shape == self.def_shape:
            self._resize(shape)

        # Otherwise, we can't use the input tensor:
        else:
            def_shape = list(str(x) for x in self.def_shape)
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
                f"Tensor Shape Mismatch; Expected {exp}, Got: `{list(shape)}`"
            )

        # Finally, if we're not doing manual batching, wrap the tensor in a list
        # so that we can pretend we're making a batch of size 1:
        if manual_batch_size == 0:
            dprint("Pseudo manual batch")
            tensor = cast(Tensor, [tensor])
            manual_batch_size = 1
        else:
            dprint(f"Manual batch of size {manual_batch_size}")

        return tensor, manual_batch_size

    def _run_batch(self, tensor: Tensor, batch_size: int) -> Tuple[Tensor, Metrics]:
        assert self.interp is not None

        input_idx = self.interp.get_input_details()[0]["index"]
        output_idx = self.interp.get_output_details()[0]["index"]

        output, exec_time = None, 0.0

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

        metrics = Metrics().time_to_execute(
            int(exec_time * (10 ** 6))
        )  # in microseconds
        # .trace("") # TODO!!

        assert output is not None
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
    # TODO: why is this annotation required. https://github.com/python/mypy/pull/5677 says it isn't.
    def __init__(self) -> None:
        self.models: List[LocalModel] = []

        # TODO: remove
        j: Callable[[str], str] = lambda name: os.path.join(MODEL_DIR, name)
        # For now, let's load mnist-lstm in as model 0:
        assert 0 == self._load_from_file(j("mnist-lstm.tflite"))
        # And mobilenet_v1_1.0_224_float as model 1:
        assert 1 == self._load_from_file(j("mobilenet_v1_1.0_224_float.tflite"))
        # And mobilenet_v1_1.0_224_quant as model 2:
        assert 2 == self._load_from_file(j("mobilenet_v1_1.0_224_quant.tflite"))
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
