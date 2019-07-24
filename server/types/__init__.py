import os
import sys
from os.path import abspath, dirname, isdir, join
from typing import Callable

from ..debug import dprint

up: Callable[[str, int], str] = lambda p, n: p if n == 0 else up(dirname(p), n - 1)

project_root = up(os.path.abspath(__file__), 3)
common_vars = join(project_root, "scripts", "common")


def get_variable_path(var: str, msg: str) -> str:
    try:
        with open(common_vars, "r") as f:
            line = next(filter(lambda l: f"{var}=" in l, f))

            if line is None:
                raise Exception(
                    f"Unable to determine {msg}; is {var} set in {common_vars}?"
                )
            else:
                return join(
                    project_root, line[line.index("=") + 1 :].rstrip().strip('"')
                )
    except FileNotFoundError:
        raise Exception(
            f"Unable to determine {msg}; is {var} still set in {common_vars}?"
        )


# Get the build directory location from the common variables script
build_dir = join(get_variable_path("PROTOC_DST_DIR", "build directory"), "python")
dprint(f"Using {build_dir} as the protobuf message module.")

if isdir(build_dir):
    sys.path.append(build_dir)
else:
    raise Exception(
        f"The python protobuf build directory doesn't seem to "
        f"exist {build_dir}; try running `pipenv run build`?"
    )


MODEL_DIR = get_variable_path("MODEL_DIR", "local model directory")
dprint(f"Using {MODEL_DIR} as the local model directory.")

from inference_pb2 import (  # isort:skip
    Error,
    InferenceRequest,
    InferenceResponse,
    LoadModelRequest,
    LoadModelResponse,
    Metrics,
    Model,
    ModelHandle,
    Tensor,
)
