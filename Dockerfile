# Dockerfile to build, test, check, and finally assemble a usable docker image
# for the web-demos project.
#
# Flow:                                                             -> Regular Dist Container -> Upload Regular Container
#                                                                  /
# Base -> Build -> Check (Lint + Format) -> Test -> Package + Test -> Upload Regular Package
#               \                                 \                \
#                -> Check Scripts                  -> Upload Cov    -> Package + Test (anew, debug) -> Upload Debug Package
#                                                                                              \
#                                                                                               -> Debug Dist Container -> Upload Debug Container
# Modified: July 24th, 2019

# Changing this will probably break everything
ARG BASE_TYPE=slim-buster
ARG PYTHON_VER=3.7.4

ARG BASE_BUILD_IMAGE=python:${PYTHON_VERSION}-${BASE_TYPE}

ARG WORKDIR="/opt/project"

# These should all match the values in `scripts/common`.
ARG PACKAGE_DIR="dist"
ARG BUILD_DIR="build"
ARG EXC_NAME="web-demos"

ARG PORT="5000"
ARG HOST="0.0.0.0"

ARG DEBUG
ARG FORCE_REBUILD=false
ARG SKIP_CHECKS=true
ARG CHECK_WHEEL=true
ARG UPLOAD_WHEEL=false

FROM ${BASE_BUILD_IMAGE} as build
ARG DEBUG
ARG WORKDIR
ARG BUILD_DIR

# Grabbing the dependencies seems to be the most time consuming part of the
# build (they appear to be built from source unnecessarily), so we'll just
# copy over the Pipfile (lists the dependencies) at first, so that the docker
# layer cache can do it's job and make things a little less painful.
#
# Note: because the Pipfile isn't _just_ dependencies, this isn't perfect but
# nor is the Pipfile (okay, pipenv gets it _almost_ perfect. scripts and
# whitespace don't factor into the lock hash at all, but somehow things like
# TOML maps do; though:
#   toml = "~=0.10.0"
# and:
#   toml = { version = "~=0.10.0" }
# are really identical, they produce different lock hashes. I'm betting pipenv
# hashes the object that the toml parser produces for the package/source
# sections. but still. pretty good). We'll rebuild on whitespace changes and
# script changes and pretty much anything that happens to these two files.
#
# Pipfile.lock is less volatile so we _could_ only pull that file in, tell
# pipenv to install from the lock file (no Pipfile; `--ignore-pipfile`), but
# then we lose our `--deploy` check (makes sure the Pipfile.lock is in sync
# with the Pipfile). Since there doesn't seem to be a way to check that the
# two are in sync without actually going and installing again, this seems like
# an okay compromise. (Also it'd be weird to install the deps and then fail
# _after_ that on the Pipfile/Pipfile.lock being out of sync. Fail fast!)
COPY Pipfile Pipfile.lock "${WORKDIR}/"
WORKDIR "${WORKDIR}"

# Local .venv so that the virtualenv gets copied to the other build stages.
# `pipenv install --deploy` will ensure the lock file is up to date.
# The last three lines are a _hack_ that exploits the marker files the current
# build system drops to make sure that we do not run `pipenv install` or
# `pipenv install --dev` again.
RUN : \
 && mkdir .venv \
 && pipenv install --dev --deploy \
 && mkdir -p "${WORKDIR}/${BUILD_DIR}/" \
 && : "These two weird looking files come from ${marker} in scripts/common." \
 && touch "${WORKDIR}/${BUILD_DIR}/.__install" \
 && touch "${WORKDIR}/${BUILD_DIR}/.__install-dev"

COPY . "${WORKDIR}"

RUN pipenv check || true # For the logs

RUN pipenv run deps
RUN pipenv run build

FROM build as check
ARG DEBUG
ARG WORKDIR

WORKDIR "${WORKDIR}"

RUN pipenv run check


FROM check as test
ARG DEBUG
ARG WORKDIR

WORKDIR "${WORKDIR}"

RUN pipenv run test


FROM check as package
ARG DEBUG
ARG FORCE_REBUILD
ARG SKIP_CHECKS
ARG CHECK_WHEEL
ARG UPLOAD_WHEEL
ARG WORKDIR

WORKDIR "${WORKDIR}"

RUN pipenv run package


FROM python:${PYTHON_VER}-${BASE_TYPE} as dist
ARG DEBUG
ARG WORKDIR
ARG HOST
ARG PORT
ARG PACKAGE_DIR
ARG EXC_NAME

COPY --from=package "${WORKDIR}/${PACKAGE_DIR}/dist/" "/opt/wheels"

RUN : \
&& apt-get update -y \
    -qq 2>/dev/null \
 && apt-get upgrade -y \
    -qq 2>/dev/null \
 && apt-get install -y \
        git \
    -qq 2>/dev/null \
 && pip3 install /opt/wheels/*.whl \
 && rm -rf /opt/wheels \
 && apt-get clean -y \
    -qq 2>/dev/null \
 && apt-get remove -y \
        git \
    -qq 2>/dev/null \
 && apt-get autoremove -y \
    -qq 2>/dev/null \
 && rm -rf \
        /var/tmp/* \
        /var/lib/apt/lists/*

RUN : \
 && echo "#!/usr/bin/env bash\n\necho; exec ${EXC_NAME} ${@}" > /bin/entrypoint \
 && chmod +x /bin/entrypoint

ENV HOST=${HOST}
ENV PORT=${PORT}

EXPOSE ${PORT}/tcp

ENTRYPOINT "/bin/entrypoint"
CMD []