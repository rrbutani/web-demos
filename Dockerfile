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

ARG NODE_VERSION=dubnium
ARG PYTHON_VER=3.7.4
ARG BASE_TYPE=alpine # Changing this will probably break everything
ARG BASE_BUILD_IMAGE=${NODE_VERSION}-${BASE_TYPE}

ARG WORKDIR="/opt/project"
ARG PACKAGE_DIR="dist"
ARG EXC_NAME="web-demos"

ARG PORT="5000"
ARG HOST="0.0.0.0"

FROM ${BASE_BUILD_IMAGE} as build
ARG WORKDIR

COPY . "${WORKDIR}"
WORKDIR "${WORKDIR}"

RUN pipenv run deps
RUN pipenv run build


FROM ${BASE_BUILD_IMAGE} as check
ARG WORKDIR

COPY --from=build "${WORKDIR}" "${WORKDIR}"
WORKDIR "${WORKDIR}"

RUN pipenv run check


FROM ${BASE_BUILD_IMAGE} as test
ARG WORKDIR

COPY --from=check "${WORKDIR}" "${WORKDIR}"
WORKDIR "${WORKDIR}"

RUN pipenv run test


FROM ${BASE_BUILD_IMAGE} as package
ARG WORKDIR

COPY --from=test "${WORKDIR}" "${WORKDIR}"
WORKDIR "${WORKDIR}"

RUN pipenv run package


FROM ${PYTHON_VER}-${BASE_TYPE} as dist
ARG HOST
ARG PORT
ARG PACKAGE_DIR
ARG EXC_NAME

COPY --from=package "${WORKDIR}/${PACKAGE_DIR}/dist/" "/opt/wheels"

RUN : \
 && pip3 install /opt/wheels/*.whl \
 && rm -rf /opt/wheels

ENV HOST=${HOST}
ENV PORT=${PORT}
EXPOSE ${PORT}/tcp # TODO

ENTRYPOINT [ "${EXC_NAME}" ]
