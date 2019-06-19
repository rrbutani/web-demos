import { inference } from "../build/messages";

// console.log(inference);

export function echo(arg : inference.Tensor) : inference.Tensor {
  return arg;
}
