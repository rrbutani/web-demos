import time
from typing import List, Tuple, Union, Optional

import numpy as np
import tensorflow as tf

from server.types.metrics import Metrics

print(f"TF Version: {tf.__version__}")
# tf.enable_eager_execution() # TODO
# tf.logging.set_verbosity(tf.logging.DEBUG) # TODO

Interpreter = tf.lite.Interpreter

Error = str
Tensor = np.ndarray
Handle = int


class LocalModel:
    def __init__(self, model: str):
        assert model is not None

        # String with the model's contents; used to set model_content in the
        # TFLite Interpreter's constructor hopefully.
        self.model: str = model

        self.interp: Optional[Interpreter] = None
        self.default_input_shape: Optional[List[int]] = None
        self.default_output_shape: Optional[List[int]] = None

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
        input_idx = input_details["index"]

        output_details = self.interp.get_output_details()[0]
        output_idx = output_details["index"]

        if tensor is None:
            return (None, 0), "Tensor was empty."

        # Type check input:
        expected = input_details["dtype"]
        actual = tensor.dtype

        if expected != actual:
            return (
                (None, 0),
                f"Tensor Type Mismatch:: Expected: {expected}, Got: {actual}",
            )

        # Shape check input:
        expected = tuple(input_details["shape"])
        actual = tensor.shape
        batch_size = 1

        if expected != actual:
            # If the tensor's shape matches the model's initial expected shape
            # or has the right shape for a batch, try to reshape the model's
            # input tensor.
            orig_len = len(self.default_input_shape)
            if actual == self.default_input_shape:
                # Reset back to normal:
                self.interp.resize_tensor_input(input_idx, self.default_input_shape)
                self.interp.resize_tensor_output(output_idx, self.default_output_shape)
                tensor = [tensor]
            elif len(actual) == orig_len + 1 and np.all(actual[-orig_len:] == self.default_input_shape):
                # If we've been asked to do a batch (and if all but the first
                # element of the shape matches, resize the input and output
                # accordingly:
                batch_size = actual[0]
                # TODO: resolve!
                # self.interp.resize_tensor_input(input_idx, [batch_size] + self.default_input_shape)
                # self.interp.resize_tensor_output(output_idx, [batch_size] + self.default_output_shape)
            else:
                return (
                    (None, 0),
                    f"Tensor Shape Mismatch:: Expected: {expected}, Got: {actual}",
                )

            self.interp.allocate_tensors()
            # elif orig_len == orig_len
        else:
            tensor = [tensor]

            # if orig_len <= len(expected) <= orig_len + 1 and actual[-orig_len:] == self.default_input_shape:
            #     print(f"Resizing input tensor from `{expected}` to `{actual}`..")
            #     self.interp.resize_tensor_input(input_idx, actual)
            #     self.interp.allocate_tensors()
            #     print("success!")
            # else:
            #     return (
            #         (None, 0),
            #         f"Tensor Shape Mismatch:: Expected: {expected}, Got: {actual}",
            #     )

        # Now try to run inference:

        output = None
        exec_time = 0
        for i in range(batch_size):
            # print(f"Part {i}: {tensor[i]}")

            # Shouldn't need to cast the array:
            self.interp.set_tensor(input_idx, tensor[i])

            begin = time.clock()
            self.interp.invoke()
            exec_time += time.clock() - begin

            output_part = self.interp.get_tensor(output_idx)
            if output is None:
                output = output_part
            else:
                output = np.append(output, output_part, axis=0)

            # output = np.append(output, self.interp.get_tensor(output_idx), axis=0)

        metrics = Metrics().time_to_execute(exec_time * (1000 ** 2))  # in milliseconds
            # .trace("") # TODO!!
        # print(f"final: {output}")
        return (output, metrics), None

        # # Shouldn't need to cast the array:
        # self.interp.set_tensor(input_idx, tensor)

        # begin = time.clock()
        # self.interp.invoke()
        # exec_time = time.clock() - begin

        # metrics = Metrics().time_to_execute(exec_time * (1000 ** 2))  # in milliseconds
        # # .trace("") # TODO!!

        # return (self.interp.get_tensor(output_idx), metrics), None


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
