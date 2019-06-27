#!/usr/bin/env python3.7

from typing import Union

import tensorflow as tf
import tensorflowjs
from flask import Flask, request, send_from_directory
from flask_pbj import api, json, protobuf

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
from server.debug import dprint, if_debug, _DEBUG

# convert: Foreign type -> Local type
# into: Local type -> Foreign type

HOST = "0.0.0.0"  # TODO: source from env var
PORT = 5000  # TODO: source from env var

app = Flask(__name__, static_folder="../examples", static_url_path="/examples/")
model_store = ModelStore()


@app.route("/api/echo/<string:string>")
def echo(string: str) -> str:
    return string


@app.route("/ex/<string:example_name>/<path:path>")
@app.route("/ex/<string:example_name>/", defaults={"path": "index.html"})
def serve_build_file(example_name: str, path: str):
    dprint(f"Trying: {example_name}/dist/{path}")
    return send_from_directory("../examples", example_name + "/dist/" + path)


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
