import {
  complex as complex_constructor,
  tensor as tfjs_tensor_constructor,
  Tensor as TfJsTensor,
} from "@tensorflow/tfjs";
import { chunk, invert, unzip } from "lodash";
import { inference } from "../build/inference";

import { exhaust } from "./util";

import PbTensor = inference.Tensor;

const sample_tfjs = tfjs_tensor_constructor([0]);
type TfJsDataType = (typeof sample_tfjs.dtype);

const sample_pb = new PbTensor();
type PbDataType = (typeof sample_pb.flat_array) & string;

/// T2P = TFJS to Protobuf
type T2PTypeMap = {
  [K in TfJsDataType]: PbDataType
};

type Constructs<T> = (properties: T) => T;

/// Protobuf to array class constructor map
type Pb2ArrMap = {
  [K in PbDataType]: Constructs<Exclude<PbTensor[K], null> | undefined>
};

// tslint:disable:object-literal-sort-keys
const type_map_tfjs2pb: T2PTypeMap = {
  float32: "floats",
  int32: "ints",
  bool: "bools",
  complex64: "complex_nums",
  string: "strings",
};
// tslint:enable:object-literal-sort-keys

// TODO: the interfaces for each kind of array are currently identical because
// each kind currently just has a single member named 'array' of type <type>[].
// Because the types for the field names are interfaces instead of classes, we
// cannot actually enforce that the constructor functions below return an
// instance belonging to the type corresponding to the field name for that type.
// I.e. `"bools": PbTensor.IntArray.create` is perfectly legal because
// IntArray.create returns an object that has an array named array in it. In
// other words, since all the array types have the same single member of similar
// types, all the array types satisfy some of the other generated array
// interfaces. And since we can only go from field name to type (PbDataType
// above), we can't effectively ensure that the constructor function matches the
// field name below.
//
// There are a couple of ways to fix this. One (kind of hokey way) is to modify
// the array types so they have member names that are different; this will
// cause their corresponding interfaces to be incompatible with each other.
//
// Something like:
// `type ConstructsAlt<F, T> = (properties: Record<F, any[]>) => T;`
// Could then be used as the type bound of values in Pb2ArrMap (with F = K).
//
// Another way is figure out some way to map between the field names and their
// matching array types at a type level. One way to do this is to modify the
// TS generator in Protobuf.js to set the type of the fields to the
// corresponding classes instead of the generated interfaces for the classes.
// TODO: this may not actually work the way I think it will; not sure whether
// class bounds actually behave differently than interface bounds (i.e.
// substructurally).
//
// Really though, the problem is that we use the number type for floats and ints
// in JavaScript. The other types are mostly okay, so I'm just going to leave
// this as is, and we'll be careful not to mix up floats and ints below.

// tslint:disable:object-literal-sort-keys
const type_map_pb_arr: Pb2ArrMap = {
  floats: PbTensor.FloatArray.create,
  ints: PbTensor.IntArray.create,
  bools: PbTensor.BoolArray.create,
  complex_nums: PbTensor.ComplexArray.create,
  strings: PbTensor.StringArray.create,
};
// tslint:enable:object-literal-sort-keys

/// P2T = Protobuf to TFJS
type P2TTypeMap = {
  [K in PbDataType]: TfJsDataType
};

type ValueUnion<T extends Record<PropertyKey, PropertyKey>> = {
  [K in keyof T]: { key: K, value: T[K] }
}[keyof T];

type Inverted<T extends Record<PropertyKey, PropertyKey>> = {
  [V in ValueUnion<T>["value"]]: Extract<ValueUnion<T>, { value: V }>["key"]
} & {};

function invert_map<T extends Record<PropertyKey, PropertyKey>>(obj: T): Inverted<T> {
  // @ts-ignore
  return invert(obj);
}

const type_map_pb2tfjs: P2TTypeMap = invert_map(type_map_tfjs2pb);

export function pb_to_tfjs_tensor(pb_tensor: PbTensor): TfJsTensor {
  const pb_dtype: PbDataType = pb_tensor.flat_array!; // TODO: handle undefined
  const dtype: TfJsDataType = type_map_pb2tfjs[pb_dtype];
  const shape = pb_tensor.dimensions as number[]; // TODO: Long?

  // See the comment on array in the tfjs_to_pb_tensor function below.
  // const array = pb_tensor[pb_dtype]!.array!;

  // TODO: handle null/undefined
  switch (pb_dtype) {
    case "floats":
    case "ints":
    case "bools":
    case "strings":
      return tfjs_tensor_constructor(pb_tensor[pb_dtype]!.array!, shape, dtype);

    case "complex_nums":
      const array = pb_tensor[pb_dtype]!.array!
        .map((c: PbTensor.Complex): number[] =>
          [c.real as number, c.imaginary as number]);

      const [reals, imags] = unzip(array);

      // TODO: this discards shape information!
      return complex_constructor(reals, imags);

    /* istanbul ignore next */
    default:
      return exhaust(pb_dtype);
  }
}

// tslint:disable-next-line:no-shadowed-variable
export async function tfjs_to_pb_tensor(tensor: TfJsTensor): Promise<PbTensor> {
  const shape = tensor.shape;
  const dtype: PbDataType = type_map_tfjs2pb[tensor.dtype];

  // Unfortunately TypeScript isn't smart enough to figure out that even though
  // ctor was set outside of the scope within which it knows dtype's type
  // because dtype is constant, it can retroactively narrow the type of ctor.
  // So, we'll have to shift this into the cases of the switch.
  // const ctor = type_map_pb_arr[dtype];
  let array;

  switch (dtype) {
    case "floats":
    case "ints":
      array = type_map_pb_arr[dtype]({
        array: Array.from(await tensor.data()),
      });
      break;

    case "bools":
      array = type_map_pb_arr[dtype]({
        array: Array.from(await tensor.data()).map((i: number): boolean => !!i),
      });
      break;

    case "strings":
      array = type_map_pb_arr[dtype]({
        array: Array.from(await tensor.data<"string">()),
      });
      break;

    case "complex_nums":
      array = type_map_pb_arr[dtype]({
        array: chunk(Array.from(await tensor.data<"complex64">()), 2)
          .map(([r, i]: [number, number]): PbTensor.Complex =>
            PbTensor.Complex.create({ real: r, imaginary: i }),
          ),
      });
      break;

    /* istanbul ignore next */
    default:
      exhaust(dtype);
  }

  return new PbTensor({
    dimensions: shape,
    [dtype]: array,
  });
}
