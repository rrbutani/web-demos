import random
from functools import reduce
from operator import mul
from typing import Any, Callable, Dict, List, Tuple, TypeVar, Union, cast

import numpy as np
import pytest

from server.debug import dprint as print
from server.types import Tensor
from server.types.tensor import (
    pb_to_tflite_tensor,
    tflite_tensor_to_pb,
    type_map_pb2numpy,
)

Shape = List[int]


def rand_float() -> float:
    return cast(float, np.random.randn())


def rand_int(bits: int = 32) -> int:
    return random.randint(-(2 ** (bits - 1)), (2 ** (bits - 1)) - 1)


def rand_bool() -> bool:
    return random.choice([True, False])


def rand_complex() -> Tuple[int, int]:
    return rand_int(64), rand_int(64)


def rand_string(max_len: int = 15) -> str:
    length = random.randint(0, max_len)

    return "".join(chr(random.randint(0, 2 ** 8)) for _ in range(length))


# No literal types...
# DataType = Union["floats", "ints", "bools", "complex_nums", "strings"]
DataType = str

type_map_pb2gen: Dict[DataType, Callable[[], Any]] = {
    "floats": rand_float,
    "ints": rand_int,
    "bools": rand_bool,
    "complex_nums": rand_complex,
    "strings": rand_string,
}


T = TypeVar("T")


def rand_tensor(
    dtype: DataType, max_dimensions: int = 5, max_len: int = 2 ** 5
) -> Tuple[Shape, List[T]]:
    dimensions: int = random.randint(0, max_dimensions)
    shape: Shape = [random.randint(1, max_len) for _ in range(dimensions)]

    total_len: int = reduce(mul, shape, 1)

    print(f"Making a {dtype} tensor with shape `{shape}` ({total_len} elements)")

    gen_func = type_map_pb2gen[dtype]
    return shape, [gen_func() for _ in range(total_len)]


def cycle(orig: np.ndarray) -> np.ndarray:
    new = pb_to_tflite_tensor(tflite_tensor_to_pb(orig))

    print(orig.dtype)
    print(orig.dtype.kind)

    assert (new == orig).all()
    assert new.shape == orig.shape
    assert new.dtype == orig.dtype

    return new


def roundtrip_single(dtype: DataType) -> None:
    orig_data: List[Any]
    orig_shape, orig_data = rand_tensor(dtype)

    np_dtype = type_map_pb2numpy[dtype]
    uno = np.array(np.reshape(orig_data, orig_shape), dtype=np_dtype)

    dos = cycle(uno)
    tres = cycle(dos)

    assert (uno == dos).all()
    assert (dos == tres).all()


def roundtrips(dtype: DataType, num_tests: int = 10) -> None:
    for _ in range(num_tests):
        roundtrip_single(dtype)


def test_float() -> None:
    roundtrips("floats")


def test_int() -> None:
    roundtrips("ints")


def test_bool() -> None:
    roundtrips("bools")


@pytest.mark.skip(reason="not fully implemented")
def test_complex() -> None:
    roundtrips("complex_nums")


@pytest.mark.skip(reason="currently unused; TODO")
def test_string() -> None:
    roundtrips("strings")
