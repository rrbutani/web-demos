
from typing import List, Tuple, Union
from timeit import timeit

import tensorflow as tf
import numpy as np

from server.types import Metrics

print(f"TF Version: {tf.__version__}")
# tf.enable_eager_execution() # TODO
# tf.logging.set_verbosity(tf.logging.DEBUG) # TODO

Interpreter = tf.lite.Interpreter

Error = str
Tensor = np.ndarray
Metrics = int

class LocalModel:
    def __init__(self, model: str):
        assert model is not None

        self.model: str = model # String with the model's contents; used to set
                                # model_content in the TFLite Interpreter's
                                # constructor hopefully.

        self.interp: Interpreter = None

    def predict(self, tensor: Tensor) -> Tuple[Tuple[Tensor, Metrics], Error]:
        assert self.model is not None

        if self.interp is None:
            # Try to load the model:
            try:
                self.interp = Interpreter(model_content=self.model)
                self.interp.allocate_tensors()
            except ValueError as e:
                return (None, 0), f"{e}"

        input_details = self.interp.get_input_details()[0]
        input_idx = input_details['index']

        output_details = self.interp.get_output_details()[0]
        output_idx = output_details['index']

        if tensor is None:
            return (None, 0), "Tensor was empty."

        # Type check input:
        expected = input_details["dtype"]
        actual = tensor.dtype

        if expected != actual:
            return ((None, 0),
                f"Tensor Type Mismatch:: Expected: {expected}, Got: {actual}")

        # Shape check input:
        expected = tuple(input_details["shape"])
        actual = tensor.shape

        if expected != actual:
            return ((None, 0),
                f"Tensor Shape Mismatch:: Expected: {expected}, Got: {actual}")

        # Now try to run inference:

        # Shouldn't need to cast the array:
        self.interp.set_tensor(input_idx, tensor)

        time = timeit(lambda i: i.inkoke(), self.interp)

        metrics = (Metrics()
            .time_t_execute(time * (1000 ** 2)))

        return (self.interp.get_tensor(output_idx), metrics), None

Handle = int

class ModelStore:
    def __init__(self):
        self.models: List[LocalModel] = []

    # Is really an infallible operation.
    def load(self, model: str) -> Tuple[Handle, Error]:
        m = LocalModel(model)

        handle = len(self.models)
        self.models.append(m)

        return handle, None

    def get(self, handle: Handle) -> Tuple[LocalModel, Error]:
        if handle >= len(self.models):
            return -1, "Invalid Handle"

        return self.models[handle], None
