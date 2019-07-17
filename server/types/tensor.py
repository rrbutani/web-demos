from functools import reduce
from operator import mul
from typing import Any, Callable, Dict, Iterable, List, Optional, Sized, Tuple, TypeVar, Type, cast

import numpy as np
from google.protobuf.message import Message

from server.types import Tensor

# TFLite Tensors are really just numpy arrays.

# In lieu of actual enums (from oneofs), we use these:

# [Protobuf field name] => numpy type
type_map_pb2numpy: Dict[str, Type[np.generic]] = {
    "floats": np.float32,
    "ints": np.int32,
    "bools": np.bool,
    "complex_nums": np.complex64,
    "strings": np.byte,
}

# [numpy kind (dtype.kind)] => Protobuf field name
type_map_numpy2pb: Dict[str, Tuple[str, Type[Any]]] = {
    "f": ("floats", Tensor.FloatArray),
    "i": ("ints", Tensor.IntArray),
    "?": ("bools", Tensor.BoolArray),
    "c": ("complex_nums", Tensor.ComplexArray),
    "S": ("strings", Tensor.StringArray),
    # We also have data types that we can't represent in the TFJS world that
    # we'll map as best as we can:
    # List of data type kinds: docs.scipy.org/doc/numpy/reference/arrays.dtypes.html
    "u": ("ints", Tensor.IntArray),  # uint8 -> int32
    "b": ("ints", Tensor.IntArray),  # signed byte -> int32
    "B": ("ints", Tensor.IntArray),  # unsigned byte -> int32
    "U": ("strings", Tensor.StringArray),  # Unicode string -> string
    # Leaving 'm' (timedelta), 'M' (datetime), 'O' (Python objects), and 'V'
    # (raw data (void)) unmapped.
}


class ConversionError(Exception):
    ...


class InvalidTensorMessage(ValueError):
    ...


class MisshapenTensor(ValueError):
    ...


T = TypeVar("T")


def _get_oneof_pair(
    m: Message, field: str, attr: Optional[str] = None
) -> Tuple[str, T]:
    """
    :raises InvalidTensorMessage: On tensors that are missing fields.
    """
    try:
        ty = m.WhichOneof(field)
    except TypeError:
        raise InvalidTensorMessage(f"Missing oneof field `{field}` on message (${m}).")
    f = getattr(m, ty)

    if attr is not None:
        f = getattr(f, attr)

    return (ty, f)


def check_shape(shape: Iterable[int], array: Sized) -> None:
    """
    :raises MisshapenTensor: On tensors with inconsistent shapes.
    """
    expected_elems = reduce(mul, shape, 1)
    actual_elems = len(array)

    if expected_elems != actual_elems:
        raise MisshapenTensor(
            f"Expected {expected_elems} elements for a tensor with {shape} dimensions, "
            f"got {actual_elems} elements."
        )


def pb_to_tflite_tensor(pb: Tensor) -> np.ndarray:
    """
    :raises MisshapenTensor: On tensors with inconsistent shapes.
    :raises InvalidTensorMessage: On tensors that are missing fields.
    """
    # numpy takes shape as a tuple of ints:
    shape = tuple(pb.dimensions)

    arr: List[int]
    pb_dtype, arr = _get_oneof_pair(pb, "flat_array", "array")
    dtype = type_map_pb2numpy[pb_dtype]

    check_shape(shape, arr)

    return np.ndarray(shape, dtype=dtype, buffer=np.array(arr, dtype=dtype))


def tflite_tensor_to_pb(tensor: np.ndarray) -> Tensor:
    """
    :raises ConversionError: On tensors that cannot be serialized.
    :raises MisshapenTensor: On tensors with inconsistent shapes.
    """
    dtype = tensor.dtype

    if not (dtype.isnative and dtype.isbuiltin):
        raise ConversionError(f"Invalid data type ({dtype}) on tensor; cannot convert.")

    field, klass = type_map_numpy2pb[dtype.kind]

    shape = tensor.shape
    array = tensor.flatten()
    check_shape(shape, array)

    array = klass(array=array)

    if array is None:
        raise ConversionError(f"Failed to create a protobuf array; tried to use `({klass})`")

    # mypy can't figure out that array will be one of the acceptable types for
    # field in Tensor because of the values in type_map_numpy2pb, but this is
    # sound (typescript, however, does understand this - check the client).
    return Tensor(**{field: array, "dimensions": shape}) # type: ignore


# Flow for moving Tensors around:
# TFJS -> Js-Proto ===> Proto ===> Py-Proto -> numpy
#            ____________________                |
#           /                    \               |
# TFJS  <-  | Protobuf Ser/Deser |  <-  numpy <=/
#           \____________________/
#
# a) Py-Proto -> numpy:
# b) numpy -> Py-Proto:
# c) TFJS -> Js-Proto:
# d) Js-Proto -> TFJS:

# Plan: (TODO)

#  3) Add a roundtrip test for serialization/deserialization of TFLite (numpy) Tensors.
#  8) Add tests for ^
