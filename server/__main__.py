#!/usr/bin/env python3.7

from os import listdir
from os.path import dirname, exists, isdir, isfile, join
from string import capwords
from typing import Union

from flask import Flask, request, render_template, send_from_directory
from flask_pbj import api, json, protobuf
import tensorflow as tf
import tensorflowjs

from server.model_store import ModelStore
from server.types import (
    InferenceRequest,
    InferenceResponse,
    LoadModelRequest,
    LoadModelResponse,
)
from server.types.error import Error, into_error
from server.types.metrics import Metrics
from server.types.model import (
    Model,
    ModelHandle,
    convert_handle,
    convert_model,
    into_handle,
)
from server.types.tensor import Tensor, pb_to_tflite_tensor, tflite_tensor_to_pb
from server.debug import _DEBUG, dprint, if_debug

# convert: Foreign type -> Local type
# into: Local type -> Foreign type

HOST = "0.0.0.0"  # TODO: source from env var
PORT = 5000  # TODO: source from env var
EX_DIR = join(dirname(__file__), "..", "examples")
TEMPLATE_DIR = join(dirname(__file__), "templates")

app = Flask(
    __name__,
    static_folder=EX_DIR,
    static_url_path="/examples/",
    template_folder=TEMPLATE_DIR,
)
model_store = ModelStore()

# snake_case/kebab-case to Title Case
def name_to_title(name: str):
    return " ".join(
        [capwords(word) for word in name.replace("_", " ").replace("-", " ").split()]
    )


@app.route("/")
@app.route("/ex/")
def example_index_page() -> str:
    examples = [
        (ex, name_to_title(ex))
        for ex in listdir(EX_DIR)
        if isdir(join(EX_DIR, ex)) and isfile(join(EX_DIR, ex, "dist", "index.html"))
    ]
    return render_template("example-index-page.html", examples=examples)


@app.route("/api/echo/<string:string>")
def echo(string: str) -> str:
    return string


@app.route("/ex/<string:example_name>/<path:path>")
@app.route("/ex/<string:example_name>/", defaults={"path": "index.html"})
def serve_build_file(example_name: str, path: str):
    p = join(example_name, "dist", path)
    dprint(f"Trying: {p}")
    return send_from_directory(EX_DIR, p)


@app.route("/api/model", methods=["POST"])
@api(json, protobuf(receives=LoadModelRequest, sends=LoadModelResponse, to_dict=False))
def load_model() -> LoadModelResponse:
    # TODO!
    pb_model: Model = request.received_message.model

    try:
        model: str = convert_model(pb_model)
        handle = model_store.load(model)

        return LoadModelResponse(handle=into_handle(handle))
    except Exception as e:
        return LoadModelResponse(error=into_error(e))


@app.route("/api/inference", methods=["POST"])
@api(json, protobuf(receives=InferenceRequest, sends=InferenceResponse, to_dict=False))
def run_inference() -> InferenceResponse:  # TODO: type sig
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


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=_DEBUG)
