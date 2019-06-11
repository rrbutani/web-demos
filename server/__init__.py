import sys
import os
from os.path import abspath, dirname, join

project_root = dirname(dirname(os.path.abspath(__file__)))
build_script = join(project_root, "scripts", "build")

# Get the build directory location from the build script
with open(build_script, "r") as f:
    line = next(filter(lambda l: "PROTOC_DST_DIR=" in l, f))

    if line is None:
        raise Error(f"Unable to determine build directory; is the build script still in {build_script}")
    else:
        build_dir = join(project_root, line[line.index('=')+1:].rstrip(), "python")
        sys.path.append(build_dir)

from inference_pb2 import Tensor
