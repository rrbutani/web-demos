from server.types import Model, ModelHandle

from typing import Tuple

# Blurring the lines here a bit
from server.model_store import LocalHandle

# TODO!!!
def convert_model(Model) -> str:
    pass

def convert_handle(model: ModelHandle) -> LocalHandle:
    return model.model

def into_handle(model: LocalHandle) -> ModelHandle:
    return ModelHandle(id=model)
