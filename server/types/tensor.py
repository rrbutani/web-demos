
import numpy as np
from typing import TypeVar, Dict, Tuple, Callable, Iterable, Sized
from google.protobuf.message import Message
from server.types import Tensor
from operator import mul
from functools import reduce
# TFLite Tensors are really just numpy arrays.

# In lieu of actual enums (from oneofs), we use these:

# [Protobuf field name] => numpy type
type_map_pb2numpy: Dict[str, np.generic] = {
    'floats': np.float32,
    'ints': np.int32,
    'bools': np.bool,
    'complex_nums': np.complex64,
    'strings': np.byte,
}

# [numpy kind (dtype.kind)] => Protobuf field name
type_map_numpy2pb: Dict[str, Tuple[str, Callable]] = {
    'f': ('floats', Tensor.FloatArray),
    'i': ('ints', Tensor.IntArray),
    'b': ('bools', Tensor.BoolArray),
    'c': ('complex_nums', Tensor.ComplexArray),
    'S': ('strings', Tensor.StringArray),
}

class ConversionError(Exception):
    ...

class InvalidTensorMessage(ValueError):
    ...

class MisshapenTensor(ValueError):
    ...

T = TypeVar('T')
def _get_oneof_pair(m: Message, field: str, attr: str = None) -> (str, T):
    try:
        ty = m.WhichOneof(field)
    except TypeError:
        raise InvalidTensorMessage(f"Missing oneof field `{field}` on message (${m}).")
    f = getattr(m, ty)

    if attr is not None:
        f = getattr(f, attr)

    return (ty, f)

def check_shape(shape: Iterable[int], array: Sized):
    expected_elems = reduce(mul, shape, 1)
    actual_elems = len(array)

    if expected_elems != actual_elems:
        raise MisshapenTensor(f"Expected {expected_elems} elements for a tensor with {shape} dimensions, got {actual_elems} elements.")

def pb_to_tflite_tensor(pb: Tensor) -> np.ndarray:
    # numpy takes shape as a tuple of ints:
    shape = tuple(pb.dimensions)

    dtype, arr = _get_oneof_pair(pb, "flat_array", "array")
    dtype = type_map_pb2numpy[dtype]

    check_shape(shape, arr)

    return np.ndarray(shape, dtype=dtype, buffer=np.array(arr, dtype=dtype))

def tflite_tensor_to_pb(tensor: np.ndarray) -> Tensor:
    dtype = tensor.dtype

    if not (dtype.isnative and dtype.isbuiltin):
        raise ConversionError(f"Invalid data type ({dtype}) on tensor; cannot convert.")

    field, klass = type_map_numpy2pb[dtype.kind]

    shape = tensor.shape
    array = tensor.flatten()
    check_shape(shape, array)

    array = klass(array=array)

    return Tensor(**{
        field: array,
        'dimensions': shape
    })

# Flow:
# TFJS(Tensor) -> Js-Proto(Tensor) ===> Proto(Tensor) ===> Py-Proto(Tensor) -> numpy(Tensor)
#                                         ____________________                       |
#                                        /                    \                      |
#                      TFJS(Tensor) <-   | Protobuf Ser/Deser |  <- numpy(Tensor) <=/
#                                        \____________________/
# a) Py-Proto -> numpy: 
# b) numpy -> Py-Proto: 
# c) TFJS -> Js-Proto:
# d) Js-Proto -> TFJS:
#

# Plan:
#  1) Python Tensor serialization/deserialization (the two functions above).
#  2) Add a tests folder + a tests script + a dev dependency for the test framework
#  3) Add a roundtrip test for serialization/deserialization of TFLite (numpy) Tensors.
#  4) Test flask-pbj and patch it up to the point where it can deserialize/serialize protobufs (don't care about JSON).
#     - if this doesn't work, do it manually for now.
#  5) Figure out how to generate protobufs for JS and how to use the JS protobuf runtime.
#  6) Create a JS package that has the protobuf runtime + can be used by the other examples.
#     - give it a build script so that it can be built by the main build script? or do it like shared
#     - test framework, later
#     - TS, later
#  7) TFJS -> Proto, Proto -> TJFS routines (async? idk)
#  8) Add tests for ^
#  9) Add an inference endpoint to the server.
#  10) Cobble together the MNIST demo (or mobilenet, I guess - hardcoded model).