
import numpy as np
from typing import TypeVar
from Protobuf import Message

# TFLite Tensors are really just numpy arrays.

# [Protobuf field name] => numpy type
type_map = {
    'floats': np.float32,
    'ints': np.int32,
    'bools': np.bool,
    'complex_nums': np.complex64,
    'strings': np.byte,
}

T = TypeVar('T')
def _get_oneof_pair(m: Message, field: str, attr: str = None) -> (str, T):
    ty = m.getOneof(field)
    f = getattr(m, ty)

    if attr != None:
        f = getattr(f, attr)

    return (ty, f)

def pb_to_tflite_tensor(pb: Tensor) -> np.ndarray:


def tflite_tensor_to_pb(tensor: np.ndarray) -> Tensor:

# Flow:
# TFJS(Tensor) -> Js-Proto(Tensor) ===> Proto(Tensor) ===> Py-Proto(Tensor) -> numpy(Tensor)
#                                        _____________________                       |
#                                       /                     \                      |
#                      TFJS(Tensor) <-  |  Protobuf Ser/Deser |  <- numpy(Tensor) <=/
#                                       \_____________________/
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