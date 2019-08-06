import re
import traceback
from typing import Any, Dict, Type

from ..debug import dprint, if_debug
from ..model_store import (
    InvalidHandleError,
    ModelLoadError,
    ModelRegisterError,
    ModelStoreFullError,
    TensorTypeError,
)
from ..ncore import InvalidDelegateLibrary, NCoreNotPresent
from ..types import Error
from ..types.tensor import InvalidTensorMessage, MisshapenTensor, TensorConversionError

# Needs to be kept in sync with the error codes from inference.proto:
# Ideally we'd use `Error.Kind` here instead of `Any` (mypy is happy with this
# fwiw) but we can't without getting runtime errors because `Error.Kind` isn't
# a normal enum since protobufs enums are specified using meta-programming
# magic.
# fmt: off
error_code_map: Dict[Type[Exception], Any] = {
    TensorConversionError:  Error.Kind.TENSOR_CONVERSION_ERROR,
    InvalidTensorMessage:   Error.Kind.INVALID_TENSOR_MESSAGE,
    MisshapenTensor:        Error.Kind.MISSHAPEN_TENSOR,
    ModelRegisterError:     Error.Kind.MODEL_REGISTER_ERROR,
    ModelStoreFullError:    Error.Kind.MODEL_STORE_FULL_ERROR,
    ModelLoadError:         Error.Kind.MODEL_LOAD_ERROR,
    InvalidHandleError:     Error.Kind.INVALID_HANDLE_ERROR,
    TensorTypeError:        Error.Kind.TENSOR_TYPE_ERROR,
    InvalidDelegateLibrary: Error.Kind.INVALID_DELEGATE_LIBRARY,
    NCoreNotPresent:        Error.Kind.NCORE_NOT_PRESENT,
}
# fmt: on

# TODO: Switch usages of this to actually pass in Exceptions
def into_error(err: Exception) -> Error:
    kind: Error.Kind = error_code_map.get(type(err), default=Error.Kind.OTHER)

    msg = " ".join(re.sub(r"([A-Z])", r" \1", err.__class__.__name__).split())
    msg = f"[{msg}] {err}"

    dprint(f"Returning Err: `{msg}`")
    _: None = if_debug(lambda: traceback.print_exc())

    return Error(kind=kind, message=f"{msg}")
