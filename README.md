# Web Demos
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

TensorFlow.js + TFLite Web Demos. These are demos for TFLite borrowed from the [TensorFlow.js Examples](https://github.com/tensorflow/tfjs-examples) and the [TensorFlow.js Models Repo](https://github.com/tensorflow/tfjs-models).

Flask Server in [`server/`](server), examples in [`examples/`](examples). The server's client-side counterpart lives in [`client/`](client).

### Running the Server
The options, ranked by difficulty:
  - Docker:
    + Build the image: (`docker build -t web-demos https://github.centtech.com/Neural/web-demos`)
    + And then run it: (`docker run -Pt web-demos`)
    + `docker ps` should tell you what port it decided to expose
  - Python Wheel:
    + `pip install <path to the wheel>`; `web-demos` should now be in your `${PATH}`
    + The tricky bit is making a wheel (`pipenv run package` will make one for you)
    + Unless you already have a wheel, use docker or the `pipenv` dev environment setup
  - `pipenv` (dev environment setup):
    + Install [this particular version](https://github.com/pypa/pipenv/tree/8ec562efc412f2a62dae231061c1b58fffe0000a) of pipenv:
      * `pip3 install "git+git://github.com/pypa/pipenv.git@${8ec562efc412f2a62dae231061c1b58fffe0000a}"`
    + Install [`pyenv`](https://github.com/pyenv/pyenv) or Python 3.7+
    + Make sure you have a modern-ish version of bash (4+; macOS users may need to upgrade)
    + Run `pipenv run run`
      * You'll be prompted to install additional dependencies if needed
      * There's a full list [here](scripts/local-deps#L10-24), but as of now this requires:
        - jq
        - a modern-ish version of bash (4+)
        - realpath
        - curl (to fetch models)
        - tar (to fetch models)
        - npm
        - yarn
        - [pipenv](https://github.com/pypa/pipenv)
        - libssl (for pip)
        - a modern-ish glibc/libstdc++ (for tensorflow)
        - a modern-ish version of git (for the clean script)
  - Manually:
    + If you don't want to use `pipenv`, you can run the server with `python -m server` or just `./server/__main__.py`. But you'll need to make sure you've got the right python version/dependencies installed manually *and* you'll have to go build the client and then the example packages! The dependencies are listed [in the Pipfile](Pipfile#L10-L16).

### Development Environment Setup
If you're making changes to the examples/server/client, you probably want to use the `pipenv` setup as described above.

Here are some of the other targets that the [Pipfile](Pipfile) offers:
  - `pipenv run deps` grabs dependencies (for the server and the examples)
  - `pipenv run dev-deps` grabs dev dependencies (for the server)
  - `pipenv run fetch` fetchs the local models (for the server)
  - `pipenv run build` rebuilds the examples and the protobuf files
  - `pipenv run clean` cleans out build files
  - `pipenv run run` gets deps and builds (if needed) and starts the server
  - `pipenv run format` grabs deps (if needed) and runs [`isort`](https://github.com/timothycrosley/isort)+[`black`](https://github.com/python/black)/[`tsfmt`](https://github.com/vvakame/typescript-formatter)+[tslint](https://github.com/palantir/tslint)
  - `pipenv run lint` runs [`mypy`](https://github.com/python/mypy)/[`tslint`](https://github.com/palantir/tslint)
  - `pipenv run test` builds and grabs deps (if needed) and runs [`pytest`](https://github.com/pytest-dev/pytest)/[`jest`](https://github.com/facebook/jest)
  - `pipenv run check` checks formatting and runs the linters
  - `pipenv run watch` rebuilds the components of the project as changes are made
  - `pipenv run package` builds a python wheel with all the assets rolled in
  - `pipenv run check-scripts`
  - `pipenv run lint-examples`

### Adding new models:
The models that the server grabs are all defined within [this script](scripts/fetch#L15-24). Models can be specified by a URL leading to a `.tflite` model or by a URL leading to a .tar.gz containing a `.tflite` model (there's more information in the script).

Examples can reference models by their filename ([here's an example](examples/coco-ssd/src/index.ts#L133-L134)) or by[ providing a URL and a model type](examples/coco-ssd/src/index.ts#L126-L127) (in the latter case, the server will go grab the model and try to use it).

### Adding new examples:
This project is set up to support the example project structure used by examples in the [tfjs-examples repo](https://github.com/tensorflow/tfjs-examples) (parcel based JavaScript project that uses TensorFlow.js) and the structure used by examples in the [tfjs-models repo](https://github.com/tensorflow/tfjs-models) (rollup.js based TypeScript project + a nested demo project that uses Parcel, Yalc, JavaScript, and TensorFlow.js).

These commits provide a good reference for how to add a tfjs-examples style example:
  - just to _build_ with the client library: 058f38a52838a968e1cd06bbbd4066b09ae72c09
    + this commit explains some more: 27fcfd25ebb03246a3a08080b2e593d8964e816d
  - making the TypeScript library in the project use the client: dfaecd7de3b329ac2afecccbc8d5ee48b6653ff9
  - actually making the demo (JavaScript project) use the client: c9aa63c8bcdc2994698cc46aecc50e562a98a1cd

And these should be helpful for adding a tfjs-models style example:
  - just one step: d0c4fe008c89d05f1bee059a3f54f973158b6946

Model conversion doesn't (currently) seem to work reliably automatically; as in the above commit it probably makes sense to add a backup model that's a local file on the server to fall back on if getting the server to convert a model with the client API fails.

Some of the converted models that this project uses (along with steps detailing how the models were converted) are in [this repo](https://github.com/rrbutani/tflite-models).

Good Luck!