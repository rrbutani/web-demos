import sys
import os
from os.path import abspath, dirname, join, isdir
from typing import Callable

up: Callable[[str, int], str] = lambda p, n: p if n == 0 else up(dirname(p), n - 1)

project_root = up(os.path.abspath(__file__), 3)
common_vars = join(project_root, "scripts", "common")

# Get the build directory location from the common variables script
try:
    with open(common_vars, "r") as f:
        line = next(filter(lambda l: "PROTOC_DST_DIR=" in l, f))

        if line is None:
            raise Exception(
                f"Unable to determine build directory; is PROTOC_DST_DIR set "
                "in {common_vars}?"
            )
        else:
            build_dir = join(
                project_root, line[line.index("=") + 1 :].rstrip(), "python"
            )
except FileNotFoundError:
    raise Exception(
        f"Unable to determine build directory; is the build script still "
        "in {common_vars}?"
    )

print(build_dir)

if isdir(build_dir):
    sys.path.append(build_dir)
else:
    raise Exception(
        f"The python protobuf build directory doesn't seem to "
        "exist {build_dir}; try running `pipenv build`?"
    )


from inference_pb2 import Error, Tensor, Model, ModelHandle, Metrics
from inference_pb2 import LoadModelRequest, LoadModelResponse
from inference_pb2 import InferenceRequest, InferenceResponse
