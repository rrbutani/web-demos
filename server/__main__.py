#!/usr/bin/env python3.7


from flask import Flask, send_from_directory, request
from flask_pbj import api, json, protobuf
from typing import Union
import tensorflow as tf
import tensorflowjs

from .types.tensor import Tensor, pb_to_tflite_tensor, tflite_tensor_to_pb


HOST = "0.0.0.0"
PORT = 5000

app = Flask(__name__, static_folder='../examples', static_url_path='/examples/')

@app.route('/api/echo/<string:string>')
def echo(string: str) -> str:
    return string

@app.route('/ex/<string:example_name>/<path:path>')
@app.route('/ex/<string:example_name>/', defaults={'path': "index.html"})
def serve_build_file(example_name: str, path: str):
    print(f"Trying: {example_name}/dist/{path}")
    return send_from_directory('../examples', example_name + "/dist/" + path)

@app.route('/api/inference', methods=['POST'])
@api(json, protobuf(receives=Tensor, sends=Tensor, to_dict=False))
def run_inference() -> Union[Tensor, Exception]: # TODO: type sig
    tensor = request.received_message
    print(tensor)

    # Round trip!
    return tflite_tensor_to_pb(pb_to_tflite_tensor(tensor))

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)
