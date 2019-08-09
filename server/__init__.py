from os import environ as env
from os import listdir
from os.path import dirname, exists, isdir, isfile, join
from string import capwords
from typing import Any, TypeVar, Union

import tensorflow as tf
import tensorflowjs
from flask import Flask, redirect, render_template, request, send_from_directory
from flask_pbj import api, json, protobuf

from .debug import _DEBUG, dprint, if_debug
from .model_store import ModelStore
from .types import (
    InferenceRequest,
    InferenceResponse,
    LoadModelRequest,
    LoadModelResponse,
)
from .types.error import Error, into_error
from .types.metrics import Metrics
from .types.model import Model, ModelHandle, convert_handle, convert_model, into_handle
from .types.tensor import Tensor, pb_to_tflite_tensor, tflite_tensor_to_pb

# convert: Foreign type -> Local type
# into: Local type -> Foreign type

HOST: str = env["HOST"] if "HOST" in env else "0.0.0.0"
PORT: int = int(env["PORT"]) if "PORT" in env else 5000
EX_DIR = join(dirname(__file__), "..", "examples")
TEMPLATE_DIR = join(dirname(__file__), "templates")

app = Flask(
    __name__,
    static_folder=EX_DIR,
    static_url_path="/examples/",
    template_folder=TEMPLATE_DIR,
)
model_store: ModelStore

# Not ideal, but good enough:
Response = Any

# snake_case/kebab-case to Title Case
def name_to_title(name: str) -> str:
    return " ".join(
        [capwords(word) for word in name.replace("_", " ").replace("-", " ").split()]
    )


@app.route("/")
def hello() -> Response:
    return redirect("ex", code=302)


@app.route("/ex/")
def example_index_page() -> Response:
    examples = [
        (ex, name_to_title(ex))
        for ex in listdir(EX_DIR)
        if isdir(join(EX_DIR, ex)) and isfile(join(EX_DIR, ex, "dist", "index.html"))
    ]
    examples.sort()
    return render_template("example-index-page.html", examples=examples)


@app.route("/api/echo/<string:string>")
def echo(string: str) -> str:
    return string


@app.route("/ex/<string:example_name>/<path:path>")
@app.route("/ex/<string:example_name>/", defaults={"path": "index.html"})
def serve_build_file(example_name: str, path: str) -> Response:
    p = join(example_name, "dist", path)
    dprint(f"Trying: {p}")
    return send_from_directory(EX_DIR, p)


@app.route("/api/load_model", methods=["POST"])
@api(json, protobuf(receives=LoadModelRequest, sends=LoadModelResponse, to_dict=False))
def load_model() -> LoadModelResponse:
    # TODO!
    pb_model: Model = request.received_message.model

    try:
        model: bytes = convert_model(pb_model)
        handle = model_store.load(model)

        return LoadModelResponse(handle=into_handle(handle))
    except Exception as e:
        return LoadModelResponse(error=into_error(e))


@app.route("/api/inference", methods=["POST"])
@api(json, protobuf(receives=InferenceRequest, sends=InferenceResponse, to_dict=False))
def run_inference() -> InferenceResponse:
    pb_tensor: Tensor = request.received_message.tensor
    pb_handle: ModelHandle = request.received_message.handle

    try:
        tensor = pb_to_tflite_tensor(pb_tensor)
        handle = model_store.get(convert_handle(pb_handle))

        tensor, metrics = handle.predict(tensor)

        return InferenceResponse(
            tensor=tflite_tensor_to_pb(tensor), metrics=metrics.into()
        )
    except Exception as e:
        return InferenceResponse(error=into_error(e))


def main() -> None:
    global model_store
    model_store = ModelStore()
    app.run(host=HOST, port=PORT, debug=_DEBUG)
