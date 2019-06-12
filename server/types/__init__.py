import sys
import os
from os.path import abspath, dirname, join

up = lambda p, n: p if n == 0 else up(dirname(p), n - 1)

project_root = up(os.path.abspath(__file__), 3)
common_vars = join(project_root, "scripts", "common")

# Get the build directory location from the build script
try:
    with open(common_vars, "r") as f:
        line = next(filter(lambda l: "PROTOC_DST_DIR=" in l, f))

        if line is None:
            raise Exception(f"Unable to determine build directory; is PROTOC_DST_DIR set in {common_vars}?")
        else:
            build_dir = join(project_root, line[line.index('=')+1:].rstrip(), "python")
            sys.path.append(build_dir)
except FileNotFoundError:
    raise Exception(f"Unable to determine build directory; is the build script still in {common_vars}?")

from inference_pb2 import Tensor
