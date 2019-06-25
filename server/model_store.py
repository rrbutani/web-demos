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

        # Shape checking isn't as straightforward as data type checking, because
        # the input tensor's shape will differ if it's a batch.
        expected = tuple(input_details["shape"])
        actual = tensor.shape
        manual_batch_size = 1

        # This means that if the input isn't the shape the interpreter is
        # currently configured for, it isn't necessarily an error.
        if expected != actual:
            def_shape = self.default_input_shape
            def_rank  = len(def_shape)

            # If the input matches the default shape for this model, we should
            # resize the interpreter's input tensor:
            if actual == def_shape:
                # Reset back to normal:
                self.interp.resize_tensor_input(input_idx, def_shape)
                self.interp.allocate_tensors()

                # Wrap the tensor up so we can treat it like a batch of 1
                tensor = [tensor]

            # If the input has an extra dimension and if its other dimensions
            # match what we expect, we've got a batch on our hands!
            elif len(actual) == def_rank + 1 and np.all(actual[-orig_len:] == def_shape):

                # First, we'll try to see if we can resize the interpreter's
                # input tensor so that it can take the batch directly. This
                # works sometimes.
                try:
                    self.interp.resize_tensor_input(input_idx, actual)
                    self.interp.allocate_tensors()

                    # If it worked, then we're good to go. We don't need to do
                    # any manual batch manipulation, so again we'll pretend that
                    # we've got a (big) batch of one:
                    tensor = [tensor]
                except ValueError as e:
                    # But for some models, this doesn't work. For those, we'll
                    # fall back to running the batch manually.

                    self.interp.resize_tensor_input(input_idx, def_shape)
                    self.interp.allocate_tensors()

                    manual_batch_size = actual[0]

                    print(f"Got an error ({e}) while trying to resize for a batch "
                          f"({expected} to {actual}). Switching to manual batch mode.")

            # If it's not a batch and not the default shape, we can't use this
            # tensor.
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
