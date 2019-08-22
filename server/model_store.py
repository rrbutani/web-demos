import os
import time
from functools import reduce
from typing import Any, Callable, Dict, Iterable, List
from typing import NoReturn as Never
from typing import Optional, Tuple, TypeVar, Union, cast

import numpy as np
import tensorflow as tf

from .debug import dprint, if_debug
from .ncore import NCORE_PRESENT, Delegate, get_ncore_delegate_instance, if_ncore
from .types import MODEL_DIR
from .types.metrics import Metrics
from .types.model import LocalHandle as Handle

dprint(f"TF Version: {tf.__version__}")
# tf.compat.v1.enable_eager_execution()
_: None = if_debug(
    lambda: tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.DEBUG)
)

Interpreter = tf.lite.Interpreter

Error = str
Tensor = np.ndarray
Tensors = List[Tensor]

ordinal: Callable[[int], str] = lambda n: (
    str(n) + {1: "st", 2: "nd", 3: "rd"}.get(n if (n < 20) else (n % 10), "th")
)


class ModelRegisterError(Exception):
    ...


class ModelStoreFullError(Exception):
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
    def __init__(self, model: Optional[bytes] = None, path: Optional[str] = None):
        """
        :raises ModelRegisterError: When given obviously incorrect models.
        """
        # String with the model's contents; used to set model_content in the
        # TFLite Interpreter's constructor.
        self.model: Optional[bytes] = model

        # Path for models that exist on disk. Models specified by path will be
        # loaded if self.model isn't set.
        self.path: Optional[str] = path

        from_str, from_file = self.model is not None, self.path is not None

        # Validate the options we were passed:
        # (this is supposed to be a switch case, I'm sorry)
        {  # type: ignore
            (True, True): self._check_bytes_model,
            (True, False): self._check_bytes_model,
            (False, True): self._check_file_model,
            (False, False): lambda: raise_err(
                ModelRegisterError("No Model specified!")
            ),
        }[(from_str, from_file)]()

        self.interp: Optional[tf.lite.Interpreter] = None

    def _check_bytes_model(self) -> None:
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
                delegate = if_ncore(get_ncore_delegate_instance)

                # From a string, if we've got it:
                if self.model is not None:
                    self.interp = Interpreter(
                        model_content=self.model, experimental_delegates=delegate
                    )
                # If not, try a file if we've got one:
                elif self.path is not None:
                    self.interp = Interpreter(
                        model_path=self.path, experimental_delegates=delegate
                    )
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

            self.interp.allocate_tensors()

            dprint("Loaded new model.")

    def _resize_internal(self, idx: int, shape: Tuple[int, ...]) -> None:
        """
        :raises RuntimeError: When the interpreter is unable to resize the tensors.
        """
        assert self.interp is not None

        input_details = self.interp.get_input_details()[idx]
        current_shape = tuple(input_details["shape"])
        input_index = input_details["index"]

        if current_shape != shape:
            dprint(f"Attempting to resize `{current_shape}` to `{shape}`..")
            self.interp.resize_tensor_input(input_index, shape)
            self.interp.allocate_tensors()
            dprint("Success!")

    def _resize(
        self, idx: int, shape: Tuple[int, ...], backup: Optional[Tuple[int, ...]] = None
    ) -> bool:
        """
        :raises RuntimeError: When the interpreter is unable to resize the tensors.
        :raises TensorTypeError: On error when bail is set to True.

        Returns True if the backup shape was used (i.e. used to set the shape).
        """
        assert self.interp is not None

        def throw(shape: Iterable[int], e: Exception) -> Never:
            raise TensorTypeError(
                f"Unable to resize the model's {ordinal(idx)} input tensor to"
                f" match the given tensor. Attempted `{shape}`"
                f" last and got `{e}`."
            )

        # Try the first shape:
        try:
            self._resize_internal(idx, shape)
            return False
        except RuntimeError as e:
            if backup is None:
                throw(shape, e)

        # Try the second shape:
        try:
            self._resize_internal(idx, backup)
            return True
        except RuntimeError as e:
            throw(backup, e)

    def _check_tensor(self, idx: int, tensor: Tensor) -> Tuple[Tensor, int]:
        """
        :raises TensorTypeError: When the given tensor cannot be used.
        """
        assert self.interp is not None

        dtype = self.interp.get_input_details()[idx]["dtype"]

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

        input_details = self.interp.get_input_details()[idx]

        def_shape: Tuple[int, ...] = tuple(input_details["shape"])
        def_rank: int = len(def_shape)

        # If we've got an extra dimension (and if the other dimensions match our
        # original shape), we'll try to load the input tensor as a batch:
        if rank == def_rank + 1 and shape[1:] == def_shape:
            # Try native batches and manual batches as a backup:
            if self._resize(idx, shape, shape[1:]):
                # If we're going with manual batches:
                manual_batch_size = shape[0]

        # If we've got the same number of dimensions but a different number of
        # the first dimension _and_ the first dimension is expected to be 1,
        # we'll also try to use the input tensor as a batch:
        elif (
            rank == def_rank
            and shape[1:] == def_shape[1:]
            and shape[0] != def_shape[0]
            and def_shape[0] == 1
        ):
            # Native batches or manual batches if that doesn't work:
            if self._resize(idx, shape, def_shape):
                # If manual batches:
                manual_batch_size = shape[0]
                tensor = np.reshape(tensor, (shape[0],) + def_shape)

        # If our model is expecting a batch of one, but the input tensor is
        # singular, wrap the input tensor to make it a batch of one:
        elif rank == def_rank - 1 and def_shape[0] == 1 and shape == def_shape[1:]:
            self._resize(idx, def_shape)
            tensor = np.reshape(tensor, def_shape)

        # If the input tensor matches the shape we're looking for, use it as is:
        elif shape == def_shape:
            self._resize(idx, shape)

        # Otherwise, we can't use the input tensor:
        else:
            def_shape_str = list(str(x) for x in def_shape)
            shapes = [def_shape_str, ["X"] + def_shape_str]
            if def_shape[0] == 1:
                exp = (
                    f"`{shapes[0]}`, `{shapes[1]}` (batch), "
                    f"`{['X'] + def_shape_str[1:]}` (batch), or "
                    f"`{def_shape_str[1:]}` (singular)"
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

    def _run_batch(
        self, batched_tensors: List[Tensor], manual_batch_size: int
    ) -> Tuple[Tensors, Metrics]:
        """
        Takes a list of tensors, each of which is batched.
        As in, batched_tensor: [num_tensors][num_batches][*(nth tensor shape)]
        """
        assert self.interp is not None

        input_idxs = [inp["index"] for inp in self.interp.get_input_details()]
        output_idxs = [out["index"] for out in self.interp.get_output_details()]

        output: List[Optional[Tensor]] = [None for i in range(len(output_idxs))]
        exec_time = 0.0

        for batch_num in range(manual_batch_size):
            for i, input_idx in enumerate(input_idxs):
                self.interp.set_tensor(input_idx, batched_tensors[i][batch_num])

            begin = time.clock()
            self.interp.invoke()
            exec_time += time.clock() - begin

            for i, output_idx in enumerate(output_idxs):
                output_part = self.interp.get_tensor(output_idx)
                if output[i] is None:
                    output[i] = output_part
                else:
                    output[i] = np.append(output[i], output_part, axis=0)

        metrics = Metrics().time_to_execute(
            int(exec_time * (10 ** 6))
        )  # in microseconds
        # .trace("") # TODO!!

        # Appease mypy:
        for tensor in output:
            assert tensor is not None

        return cast(Tensors, output), metrics

    def predict(self, tensors: Optional[Tensors]) -> Tuple[Tensors, Metrics]:
        """
        :raises TensorTypeError: When the given tensor doesn't match the model.
        :raises ModelLoadError: If the given model cannot be loaded.
        """

        # Load the model if it's not already loaded:
        self._prepare_interpreter()

        # Check that we actually got something:
        if tensors is None:
            raise TensorTypeError("Got an empty set of input Tensors.")

        # mypy doesn't yet know this can't be None after
        # self._prepare_interpreter() is called
        assert self.interp is not None

        # Check that we have the _right_ number of input tensors:
        expected_input_tensors = len(self.interp.get_input_details())
        actual_input_tensors = len(tensors)

        if expected_input_tensors != actual_input_tensors:
            raise TensorTypeError(
                f"We were expecting {expected_input_tensors} input tensors, but "
                f"we got {actual_input_tensors} tensors."
            )

        # Then go check that each of those tensors is valid and matches what the
        # model was expecting:
        checked_tensors: List[Tuple[Tensor, int]] = [
            self._check_tensor(*t) for t in enumerate(tensors)
        ]

        # Here's the tricky bit: batching when we have multiple input tensors.
        # In order for this to work, all the input tensors must agree on the
        # number of manual batches:
        manual_batch_sizes = [s for _, s in checked_tensors]
        same_batch_size: bool = reduce(
            lambda l, r: l and r,
            (s == manual_batch_sizes[0] for _, s in checked_tensors),
        )

        if not same_batch_size:
            raise TensorTypeError(
                f"The given input tensors don't agree on a manual batch size."
                f"We tried to use these batch sizes: `{manual_batch_sizes}`."
                f"The input tensors had these shapes after resizing: "
                f"`{[t.shape for t, _ in checked_tensors]}.`"
            )

        # Note that the case where some but not all of the input tensors manage
        # to get their input tensors resized is handled here: the tensors that
        # did not manage to get their input tensor resized would have a manual
        # batch size that isn't 1.
        #
        # We're definitely assuming that the model won't allow resizing input
        # tensors in ways that aren't supported. For example, for a model that
        # takes two tensors ([10, 10] and [5, 15]) and with a batch size of 5,
        # hopefully, if the model allows the first tensor to be resized to
        # [5, 10, 10], it wouldn't allow the second tensor to be resize to, say,
        # [9, 5, 15] (i.e. hopefully it'll recognize that the batch size will
        # be the same).
        #
        # We no longer cache the expected shape/rank in case the interpreter
        # does go update these for other input tensors when an input is resized.
        #
        # If the above isn't true, we'll get runtime errors, probably.
        # FWIW, I haven't yet come across any models that actually allow input
        # tensor resizing.
        #
        # But anyways, assuming the above is true (i.e. the model enforces
        # that tensors have the same _native_ batch size), this should be sound.
        # On our end we just need to make sure the _manual_ batch sizes are the
        # same, which we just did.

        # If the tensors all do agree on a batch size, we now have to consider
        # the shapes of our input tensors and the batch. Using our
        # ([10, 10], [5, 15]) input tensor example again, if we've got a manual
        # batch size of 7, the list of our checked tensors is going to look like
        # this:
        #   [ [7, 10, 10], [7, 5, 15] ]
        #   i.e. [num_input_tensors][num_batches][*(nth input tensor shape)]]
        #
        # Ideally, we'd have something like this:
        #   [ [10, 10], [5, 15]
        #   , [10, 10], [5, 15]
        #   , [10, 10], [5, 15]
        #   , [10, 10], [5, 15]
        #   , [10, 10], [5, 15]
        #   , [10, 10], [5, 15]
        #   , [10, 10], [5, 15]
        #   ]
        #   i.e. [num_batches][num_input_tensors][*(nth input tensor shape)]]
        #
        # But no matter. We'll just adjust _run_batch to use the first form so
        # we don't have to reshape things.

        batched_tensors: List[Tensor] = [t for t, _ in checked_tensors]

        # And finally, try to run inference:
        try:
            return self._run_batch(batched_tensors, manual_batch_sizes[0])
        except Exception as e:
            raise Exception(
                f"Encountered an error while trying to run inference: `{e}`."
            )


class ModelStore:
    # TODO: why is this annotation required. https://git.io/fjbSz says it isn't.
    def __init__(self) -> None:
        self.models: List[LocalModel] = []
        self.model_table: Dict[Tuple[Optional[bytes], Optional[str]], Handle] = {}

    # If we had literal types (const generics) this would be Union[None, False, Handle]
    Check = Union[None, bool, Handle]

    def _check_model_store(
        self, model: Optional[bytes] = None, path: Optional[str] = None
    ) -> Check:
        """
        Takes the model string/path that we're trying to make a new model with.
        Returns:
          - None if no new models can be constructed.
          - False if the model does not already exist
          - a Handle corresponding to the model if it already exists
        """
        if NCORE_PRESENT and len(self.models) >= 1:
            # NCore's driver/loadable caching can currently handle 1 model at a time.
            assert len(self.models) == 1
            return None

        # If we've already loaded this model, return its handle:
        model_ident: Tuple[Optional[bytes], Optional[str]] = (model, path)
        if model_ident in self.model_table:
            return self.model_table[model_ident]

        # Otherwise, tell the callee to make their own model:
        return False

    def _load_or_use_cached(
        self, check: Check, load_func: Callable[[], LocalModel], model: str
    ) -> Handle:
        """
        :raises ModelStoreFullError: When the model store is unable to load mode models.
        """
        if check is None:
            raise ModelStoreFullError(
                "We're unable to load more models, so we're dropping the load model"
                f" request for `{model}`."
            )
        elif check is False:
            m: LocalModel = load_func()
            self.models.append(m)
            idx: Handle = len(self.models) - 1

            # Add to the model table:
            self.model_table[(m.model, m.path)] = idx

            return idx
        else:
            dprint(f"Using cache for model `{model}`")
            return check

    def load(self, model: bytes) -> Handle:
        """
        :raises ModelRegisterError: When given an obviously incorrect model.
        :raises ModelStoreFullError: When the model store is unable to load more models.
        """
        return self._load_or_use_cached(
            self._check_model_store(model=model),
            lambda: LocalModel(model=model),
            f"<from string with hash '{hash(model)}'>",
        )

    def _load_from_file(self, path: str) -> Handle:
        """
        :raises ModelRegisterError: When given an obviously incorrect model.
        :raises ModelStoreFullError: When the model store is unable to load more models.
        """
        return self._load_or_use_cached(
            self._check_model_store(path=path), lambda: LocalModel(path=path), path
        )

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
