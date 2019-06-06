#!/usr/bin/env python3.7

from flask import Flask, send_from_directory
# request, send_from_directory
# from typing import str

HOST = "0.0.0.0"
PORT = 5000

app = Flask(__name__, static_folder='../examples', static_url_path='/examples/')

@app.route('/ex/<string:example_name>/<path:path>')
@app.route('/ex/<string:example_name>/', defaults={'path': "index.html"})
def serve_build_file(example_name: str, path: str):
    print(f"Trying: {example_name}/dist/{path}")
    return send_from_directory('../examples', example_name + "/dist/" + path)

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=True)
