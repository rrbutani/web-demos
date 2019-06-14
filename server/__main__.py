#!/usr/bin/env python3.7


from flask import Flask, send_from_directory, request
from flask_pbj import api, json, protobuf
from typing import Union
import tensorflow as tf
import tensorflowjs

from server.types.tensor import Tensor, pb_to_tflite_tensor, tflite_tensor_to_pb
from server.types.model import Model, convert_model, convert_handle, into_handle
from server.types.error import Error, into_error
from server.types.metrics import Metrics, into_metrics
from server.types import LoadModelRequest, LoadModelResponse
from server.types import InferenceRequest, InferenceResponse

from server.model_store import ModelStore
from server.inference import TFLiteInterpreter

# convert: Foreign type -> Local type
# into: Local type -> Foreign type

HOST = "0.0.0.0"
PORT = 5000

app = Flask(__name__, static_folder='../examples', static_url_path='/examples/')
model_store = ModelStore()
interpreter = TFLiteInterpreter()

@app.route('/api/echo/<string:string>')
def echo(string: str) -> str:
    return string

@app.route('/ex/<string:example_name>/<path:path>')
@app.route('/ex/<string:example_name>/', defaults={'path': "index.html"})
def serve_build_file(example_name: str, path: str):
    print(f"Trying: {example_name}/dist/{path}")
    return send_from_directory('../examples', example_name + "/dist/" + path)

@app.route('/api/model', methods=['POST'])
@api(json, protobuf(receives=LoadModelRequest, sends=LoadModelResponse))
def load_model() -> LoadModelResponse:
    # TODO!
    model: Model = request.received_message.model

    handle, err = model_store.load(convert_model(model))

    if err is not None:
        response = LoadModelResponse(error=into_error(err))
    else:
        response = LoadModelResponse(handle=into_handle(handle))

    return response


@app.route('/api/inference', methods=['POST'])
@api(json, protobuf(receives=InferenceRequest, sends=InferenceResponse, to_dict=False))
def run_inference() -> InferenceResponse: # TODO: type sig
    tensor: Tensor = request.received_message.tensor
    tensor = pb_to_tflite_tensor(tensor)
    print(tensor)

    handle: Handle = request.received_message.handle

    model = model_store.get(convert_handle(handle))

    (tensor, metrics), err = interpreter.predict(model, tensor)

    if err is not None:
        response = InferenceResponse(error=into_error(err))
    else:
        tensor: Tensor = tflite_tensor_to_pb(tensor)
        metrics: Metrics = into_metrics(metrics)
        response = InferenceResponse(tensor=tensor, metrics=metrics)

    return response

    # Round trip!
    # return tflite_tensor_to_pb(tensor)

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)
