from typing import Any, Dict, Callable, Optional, NoReturn as Never
from os import environ
from os.path import join
from tempfile import mkdtemp
import urllib
from urllib.request import urlretrieve as download
import zipfile
from shutil import rmtree, copyfile

from ..types import Model, ModelHandle
from ..types.Model.Type import *

LocalHandle = int

DELETE_MODELS_AFTER_CONVERSION: bool = environ.get("DELETE_MODELS_AFTER_CONVERSION", "false").lower() == "true"

class ModelAcquireError(Exception):
    ...

class ModelDataError(Exception):
    ...

class ModelConversionError(Exception):
    ...

ModelType = Model.Type
ConversionFunc = Callable[[str, str], str]

# Same deal with the Enum types here as in `error.py`; protobuf enums are not
# actually python enums, so we're going to have to use a trick:
if True: ModelType: Type[Any] = Any  # type: ignore

# fmt: off
model_type_to_path: Dict[ModelType, str] = {
    TFLITE_FLAT_BUFFER: "tflite_model.tflite",
    TF_SAVED_MODEL:     "tf_saved_model/",
    KERAS_HDF5:         "keras_model.h5",
    KERAS_SAVED_MODEL:  "keras_saved_model/",
    KERAS_OTHER:        "",
    TFJS_LAYERS:        "tfjs_layers_model.json",
    TFJS_GRAPH:         "tfjs_graph_model/",
    TF_HUB:             "",
    GRAPH_DEFS:         "",
}
# fmt: on

# fmt: off
# [Input Format] => (dir, file) -> TFLite model as a string
model_conversion_steps: Dict[ModelType, ConversionFunc] = {
    TFLITE_FLAT_BUFFER: lambda _, f: open(f, "rb").read(),
    TF_SAVED_MODEL:     tf_saved_model_to_tflite,
    KERAS_HDF5:         keras_hdf5_to_tflite,
    KERAS_SAVED_MODEL:  keras_saved_model_to_tfjs_layers,
    KERAS_OTHER:        keras_other_to_tfjs_layers,
    TFJS_LAYERS:        tfjs_layers_to_keras_hdf5,
    TFJS_GRAPH:         lambda _, _: _unimplemented(TFJS_GRAPH),
    TF_HUB:             lambda _, _: _unimplemented(TF_HUB),
    GRAPH_DEFS:         lambda _, _: _unimplemented(GRAPH_DEFS),
}
# fmt: on

def get_path_for_model_type(model_type: ModelType, directory: str) -> str:
    """
    :raises ModelConversionError <TODO!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!>
    """
    model = model_type_to_path.get(model_type)

    if model is None:
        raise ModelConversionError(f"Unsupported model type (`{n(model_type)}`): File path for this type isn't known!")

    return model


p: Callable[[ModelPath], str] = get_path_for_model_type
n: Callable[[ModelType], str] = name_model_type = lambda type: Model.Type.Name(type)

def _unimplemented(model_type: ModelType) -> Never:
    """
    :raises ModelConversionError <TODO!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!>
    """
    raise ModelConversionError(f"Sorry! Converting `{n(model_type)}` models isn't supported yet.")

def conversion_step(model_type: ModelType, directory: str) -> str:
    """
    :raises ModelConversionError <TODO!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!>
    """
    func: Optional[ConversionFunc] = model_conversion_steps.get(model_type)
    model: str = get_path_for_model_type(model_type, directory)

    if func is None:
        raise ModelConversionError(f"Unsupported model type (`{n(model_type)}`): No conversion function available!")

    return func(directory, model)

def tf_saved_model_to_tflite(directory: str, input_dir: str) -> str:
    """
    :raises ModelConversionError <TODO!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!>
    """
    target = TFLITE_FLAT_BUFFER
    output = p(target, directory)

    ...
    TODO

    return conversion_step(target, directory)

def keras_hdf5_to_tflite(directory: str, input_dir: str) -> str:
    """
    :raises ModelConversionError <TODO!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!>
    """
    target = TFLITE_FLAT_BUFFER
    output = p(target, directory)

    ...
    TODO

    return conversion_step(target, directory)

def keras_saved_model_to_tfjs_layers(directory: str, input_dir: str) -> str:
    """
    :raises ModelConversionError <TODO!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!>
    """
    target = TFJS_LAYERS
    output = p(target, directory)

    ...
    TODO

    return conversion_step(target, directory)

def keras_other_to_tfjs_layers(directory: str, input_dir: str) -> str:
    """
    :raises ModelConversionError <TODO!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!>
    """
    target = TFJS_LAYERS
    output = p(target, directory)

    ...
    TODO

    return conversion_step(target, directory)

def tfjs_layers_to_keras_hdf5(directory: str, input_dir: str) -> str:
    """
    :raises ModelConversionError <TODO!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!>
    """
    target = KERAS_HDF5
    output = p(target, directory)

    ...
    TODO

    return conversion_step(target, directory)

# TODO!!!
def convert_model(model: Model) -> str:
    """
    :raises ModelAcquireError <TODO!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!>
    :raises ModelConversionError <TODO!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!>
    :raises ModelDataError <TODO!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!>
    """

    # Check that we've got a data source:
    try:
        source: str = model.WhichOneof("source")
        data: str = getattr(mode, source)
    except TypeError:
        raise ModelDataError(f"Model is missing a source (`{model}`).")

    # For model type, we have no way of checking that we really have it; if it
    # wasn't specified we'll get 0 (TFLITE_FLAT_BUFFER). This is fine for now.
    model_type = model.type

    directory = mkdtemp(prefix=f"{__name__}-")
    cleanup: Callable[[], None] = lambda: rmtree(directory) if DELETE_MODELS_AFTER_CONVERSION else None

    try:
        # Create a file for the model, no matter the source:
        orig_model = join(directory, "original")

        if source == "url":
            download(data, filename=orig_model)
        elif source == "data":
            with open(orig_model, "wb") as f: f.write(data)
        else: raise ModelDataError(f"Model has a source type we don't know how to handle (`{source}`).")

        # Move the model into it's right place, unzipping it if needed:
        target_model_path: str = get_path_for_model_type(model_type, directory)

        # If the model path we're trying to make ends in a slash, it's a
        # directory meaning it should have been given to us as a .zip file:
        if target_model_path[-1] == "/":
            # TODO: do we need to mkdir?
            with zipfile.ZipFile(orig_model, mode="r") as z: z.extractall(path=target_model_path)

        # Otherwise, just copy the file to the expected path:
        else: copyfile(orig_model, target_model_path)

        # Finally, with all of that out of the way, kick off the conversion:
        tflite_str_model = conversion_step(model_type, directory)

    # Identify Acquire Errors and let other errors propagate through, unchanged:
    except (ValueError, urllib.error) as e:
        raise ModelAcquireError(f"Encountered an error while trying to get the model from `{data}`: `{e}`")

    except zipfile.BadZipFile as e:
        raise ModelDataError(f"Encountered an error while trying to unzip the data provided for the model: `{e}`; "
                             f"did you remember to zip the model folder? (We expect a zipped folder for models of type {model_type})")

    # If we hit any kind of error, clean up:
    finally: cleanup()

    # If we made it, we're done!
    return tflite_str_model


def convert_handle(handle: ModelHandle) -> LocalHandle:
    return handle.id


def into_handle(handle: LocalHandle) -> ModelHandle:
    return ModelHandle(id=handle)
