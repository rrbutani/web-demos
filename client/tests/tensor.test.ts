import { complex, tensor as tfjs_tensor_constructor, Tensor as TfJsTensor } from "@tensorflow/tfjs";

import { pb_to_tfjs_tensor as pb2js, tfjs_to_pb_tensor as js2pb } from '../src/tensor';
import { exhaust } from '../src/util';

const sample_tfjs = tfjs_tensor_constructor([0]);
type TfJsDataType = (typeof sample_tfjs.dtype);

const RANDOM_STRING_MAX_LEN: number = 15;

function random_float_inclusive(min: number, max: number): number {
  return min + (Math.random() * (max - min));
}

function random_int_inclusive(min: number, max: number): number {
  const lower: number = Math.ceil(min);
  const upper: number = Math.floor(max);

  return Math.floor(random_float_inclusive(lower, upper));
}

function random_int_with_bits(bits: number): number {
  return random_int_inclusive(- (2 ** (bits - 1)), (2 ** (bits - 1)) - 1);
}

function range(max: number, min: number = 0): number[] {
  const lower: number = Math.floor(min);
  const upper: number = Math.ceil(max) - 1;

  return Array.from(Array(upper - lower).keys()).map(i => i + lower)
}

function random_tensor(dtype: TfJsDataType, max_dimensions: number = 5, max_len: number = 2 ** 5): TfJsTensor {
  const num_dimensions: number = random_int_inclusive(0, max_dimensions);
  const shape: number[] = range(num_dimensions).map(_ => random_int_inclusive(1, max_len));

  const total_len: number = shape.reduce((acc, curr) => acc * curr, 1);

  let arr: any[];

  // Some aliases:
  const rf = random_float_inclusive;
  const ri = random_int_inclusive;
  const rb = random_int_with_bits;

  switch (dtype) {
    case "float32":
      arr = range(total_len).map(_ => rf(rb(32), rb(32)));
      break;

    case "int32":
      arr = range(total_len).map(_ => rb(32));
      break;

    case "bool":
      arr = range(total_len).map(_ => ri(0, 1)).map(b => b === 0 ? false : true);
      break;

    // Complex tensors have a special constructor; they'll get fully
    // constructed here.
    // (The regular constructor accepts dtype = "complex64" but will raise an
    // error saying to use tf.complex - I think it only 'accepts' complex64 in
    // the first place so that it can be type compatible with all the other
    // things that use tensor.dtype)
    case "complex64":
      const reals = range(total_len).map(_ => rf(rb(32), rb(32)));
      const imags = range(total_len).map(_ => rf(rb(32), rb(32)));
      return complex(reals, imags);

    case "string":
      arr = range(total_len).map(_ =>
        range(ri(0, RANDOM_STRING_MAX_LEN))
          .map(_ => ri(0, 2 ** 8 - 1))
          .map(i => String.fromCharCode(i))
          .join(''));
      break;

    default:
      return exhaust(dtype);
  }

  return tfjs_tensor_constructor(arr, shape, dtype);
}

async function cycle(orig: TfJsTensor): Promise<TfJsTensor> {
  const nouveau: TfJsTensor = pb2js(await js2pb(orig));

  expect(nouveau.shape).toEqual(orig.shape);
  expect(nouveau.dtype).toEqual(orig.dtype);
  expect(await nouveau.data()).toEqual(await orig.data())

  expect(nouveau).toEqual(orig);

  return nouveau;
}

async function dtype_test(dtype: TfJsDataType) {
  const uno = random_tensor(dtype);

  const dos = await cycle(uno);
  const tres = await cycle(dos);

  expect(await uno.data()).toEqual(await tres.data());
}

describe("Tensor Roundtrip Tests", () => {
  test("floats", async _ => dtype_test("float32"));

  test("ints", async _ => dtype_test("int32"));

  test("bools", async _ => dtype_test("bool"));

  test("complex", async _ => dtype_test("complex64"));

  test("strings", async _ => dtype_test("string"));
});
