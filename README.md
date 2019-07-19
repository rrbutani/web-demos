# Web Demos

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

Flask Server in [`server/`](server), examples in [`examples/`](examples). The server's client-side counterpart lives in [`examples/client/`](examples/client). A work in progress.

Currently requires:
  - jq
  - a modern-ish version of bash (4+)
  - realpath
  - curl (to fetch models)
  - tar (to fetch models)
  - npm
  - [pipenv](https://github.com/pypa/pipenv) (older versions may have trouble)
  - libssl (for pip)
  - a modern-ish glibc/libstdc++ (for tensorflow)
  - a modern-ish version of git (for the clean script)

Run with `pipenv run run`. It _should_ just work.

We've got other targets too:
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

If you're just looking to run the server and use the example, `pipenv run run` should be all you need.

If you don't want to use `pipenv`, you can run the server with `python -m server` or just `./server/__main__.py`. But you'll need to make sure you've got the right python version/dependencies installed manually *and* you'll have to go build the client and then the example packages! The dependencies are listed [in the Pipfile](Pipfile#L10-L16).

Currently:
 - [ ] TODO: license (apache 2.0 as well - MIT is more permissive so we can't use it) + blurb about it being the same as the things we used from external sources
 - [x] TODO: format all
 - [x] TODO: rename
 - [ ] TODO: write README
 - [ ] TODO: credits
 - [x] TODO: use exceptions instead of explicit err return types
 - [x] TODO: debug env var for the server
 - [ ] TODO: debug env var for the client
 - [ ] TODO: add badges for black, license (apache), etc.
 - [ ] TODO: docker container that builds and then runs the entire thing (args for  PORT that go and expose the same port after)
 - [ ] TODO: comment protobuf file(s)
 - [ ] TODO: reorder targets in this readme and add the lint target
 - [ ] TODO: Document the build system env vars (DEBUG_BUILD, FORCE_REBUILD)
