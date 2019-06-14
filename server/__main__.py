#!/usr/bin/env python3.7


from flask import Flask, send_from_directory, request
from flask_pbj import api, json, protobuf
from typing import Union
import tensorflow as tf
import tensorflowjs

from server.types.tensor import Tensor, pb_to_tflite_tensor, tflite_tensor_to_pb
from server.types.model import Model, ModelHandle, convert_model, convert_handle, into_handle
from server.types.error import Error, into_error
from server.types.metrics import Metrics
from server.types import LoadModelRequest, LoadModelResponse
from server.types import InferenceRequest, InferenceResponse

from server.model_store import ModelStore

# convert: Foreign type -> Local type
# into: Local type -> Foreign type

HOST = "0.0.0.0"
PORT = 5000

app = Flask(__name__, static_folder='../examples', static_url_path='/examples/')
model_store = ModelStore()

@app.route('/api/echo/<string:string>')
def echo(string: str) -> str:
    return string

@app.route('/ex/<string:example_name>/<path:path>')
@app.route('/ex/<string:example_name>/', defaults={'path': "index.html"})
def serve_build_file(example_name: str, path: str):
    print(f"Trying: {example_name}/dist/{path}")
    return send_from_directory('../examples', example_name + "/dist/" + path)

@app.route('/api/model', methods=['POST'])
@api(json, protobuf(receives=LoadModelRequest, sends=LoadModelResponse, to_dict=False))
def load_model() -> LoadModelResponse:
    # TODO!
    model: Model = request.received_message.model

    model, err = convert_model(model)
    handle, err = model_store.load(model)

    if err is not None:
        response = LoadModelResponse(error=into_error(err))
    else:
        response = LoadModelResponse(handle=into_handle(handle))

    return response


@app.route('/api/inference', methods=['POST'])
@api(json, protobuf(receives=InferenceRequest, sends=InferenceResponse, to_dict=False))
def run_inference() -> InferenceResponse: # TODO: type sig
    tensor: Tensor = request.received_message.tensor

    try:
        tensor = pb_to_tflite_tensor(tensor)
    except Exception as e:
        return InferenceResponse(error=into_error(e))

    handle: ModelHandle = request.received_message.handle

    handle, err = model_store.get(convert_handle(handle))

    if err is not None:
        return InferenceResponse(error=into_error(err))

    (tensor, metrics), err = handle.predict(tensor)

    if err is not None:
        return InferenceResponse(error=into_error(err))

    try:
        tensor: Tensor = tflite_tensor_to_pb(tensor)
    except Exception as e:
        return InferenceResponse(error=into_error(err))

    response = InferenceResponse(tensor=tensor, metrics=metrics.into())

    return response

    # Round trip!
    # return tflite_tensor_to_pb(tensor)

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)
