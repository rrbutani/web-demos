import { Tensor as TfJsTensor } from "@tensorflow/tfjs";
import { fetch } from "cross-fetch";

import { inference } from "../build/inference";

import { Metrics } from "./metrics";
import { pb_to_tfjs_tensor, tfjs_to_pb_tensor } from "./tensor";
import { dprint } from "./util";

import PbTensor = inference.Tensor;
import Req = inference.InferenceRequest;
import Resp = inference.InferenceResponse;
import Handle = inference.ModelHandle;
import PbError = inference.Error;
import PbMetrics = inference.Metrics;

function print_error(err: PbError): string {
  return `Kind: ${err.kind}, Message: ${err.message}`;
}

PbError.toString = function(): string {
  // @ts-ignore
  return print_error(this);
};

async function extract(resp: Response): Promise<Uint8Array> {
  return new Uint8Array(await resp.arrayBuffer());
}

export class Model {

  public static MnistModel = new Model(new Handle({ id: 0 }));
  public static MobileNetFloatModel = new Model(new Handle({ id: 1 }));
  public static MobileNetQuantModel = new Model(new Handle({ id: 2 }));
  public handle: Handle;

  private constructor(handle: Handle) {
    this.handle = handle;
  }

  // // TODO
  // static load_model(model: urlLike | ByteString): Model {

  // }

  public async predict_with_metrics(tensor: TfJsTensor): Promise<[TfJsTensor, Metrics]> {
    const request: Req = new Req({
      handle: this.handle,
      tensor: await tfjs_to_pb_tensor(tensor),
    });

    const raw_response = await fetch(
      `/api/inference`,
      {
        body: Req.encode(request).finish(),
        headers:
        {
          "Accept": "application/x-protobuf",
          "Content-Type": "application/x-protobuf",
        },
        method: "POST",
      },
    );

    const response: Resp = Resp.decode(await extract(raw_response));

    if (response.response === "tensor" && response.tensor instanceof PbTensor) {
      if (!(response.metrics instanceof PbMetrics)) {
        throw Error(`No Metrics in response.`);
      }

      const metrics: Metrics = Metrics.from(response.metrics);
      dprint(`Took ${metrics.time_to_execute} μs.`);

      return [pb_to_tfjs_tensor(response.tensor), metrics];
    } else if (response.response === "error" && response.error instanceof PbError) {
      throw Error(`Got an error: '${print_error(response.error)}'`);
    } else {
      throw Error(`Invalid Response; expected tensor or error, got '${response.response}'`);
    }
  }

  public async predict(tensor: TfJsTensor): Promise<TfJsTensor> {
    return (await this.predict_with_metrics(tensor))[0];
  }
}

export const MnistModel = Model.MnistModel;
export const MobileNetFloatModel = Model.MobileNetFloatModel;
export const MobileNetQuantModel = Model.MobileNetQuantModel;
