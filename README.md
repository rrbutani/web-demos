# TFLite Examples Repo

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

Flask Server in `server/`, examples in `examples/`. A work in progress.

Currently requires:
  - jq
  - a modern-ish version of bash (4+)
  - npm
  - [pipenv](https://github.com/pypa/pipenv) (older versions may have trouble)

Run with `pipenv run run`. It _should_ just work.

We've got other targets too:
  - `pipenv run deps` grabs dependencies (for the server and the examples)
  - `pipenv run dev-deps` grabs dev dependencies (for the server)
  - `pipenv run build` rebuilds the examples and the protobuf files
  - `pipenv run clean` cleans out build files
  - `pipenv run run` gets deps and builds (if needed) and starts the server
  - `pipenv run format` grabs deps (if needed) and runs [black](https://github.com/python/black)
  - `pipenv run test` builds and grabs deps (if needed) and runs [pytest](https://github.com/pytest-dev/pytest)

If you're just looking to run the server and use the example, `pipenv run run` should be all you need.

If you don't want to use `pipenv`, you can run the server with `python -m server` or just `./server/__main__.py`. But you'll need to make sure you've got the right python version/dependencies installed manually! They're listed [in the Pipfile](Pipfile).

TODO: license (apache 2.0 as well - MIT is more permissive so we can't use it) + blurb about it being the same as the things we used from external sources
TODO: format all
TODO: rename
TODO: write README
TODO: credits
TODO: use exceptions instead of explicit err return types
TODO: debug env var
TODO: add badges for black, license (apache), etc.