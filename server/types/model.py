from typing import Tuple, cast

# Blurring the lines here a bit
from ..model_store import Handle as LocalHandle
from ..types import Model, ModelHandle

class ModelAcquireError(Exception):
    ...

class ModelConversionError(Exception):
    ...

# TODO!!!
def convert_model(model: Model) -> str:
    pass


def convert_handle(handle: ModelHandle) -> LocalHandle:
    return handle.id


def into_handle(handle: LocalHandle) -> ModelHandle:
    return ModelHandle(id=handle)
