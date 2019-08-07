import { Tensor as TfJsTensor } from "@tensorflow/tfjs";
import { fetch } from "cross-fetch";
import { Reader, Writer } from "protobufjs";

import { inference } from "../build/inference";

import { Metrics } from "./metrics";
import { pb_to_tfjs_tensor, tfjs_to_pb_tensor } from "./tensor";
import { dprint } from "./util";

import PbTensor = inference.Tensor;
import PbModel = inference.Model;
import ModelReq = inference.LoadModelRequest;
import ModelResp = inference.LoadModelResponse;
import InfReq = inference.InferenceRequest;
import InfResp = inference.InferenceResponse;
import Handle = inference.ModelHandle;
import PbError = inference.Error;
import PbMetrics = inference.Metrics;

export type ModelType = PbModel.Type;

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

const headers = {
  "Accept": "appplication/x-protobuf",
  "Content-Type": "appplication/x-protobuf",
};

type URL = string; // TODO: this isn't great; it's a stop gap

interface IPReq<Req, Resp> {
  encode(message: Req, writer?: Writer): Writer;
  decode(reader: (Reader | Uint8Array), length?: number): Resp;
}

interface IPRsp {
  response?: string;
  error?: (inference.IError | null);
}

async function proto_request<Req, Rsp extends IPRsp, W extends IPReq<Req, Rsp>>(
  endpoint: URL, req: Req, witness: W): Promise<Rsp> {
  const raw_response = await fetch(
    endpoint,
    {
      body: witness.encode(req).finish(),
      headers,
      method: "POST",
    },
  );

  const response: Rsp = witness.decode(await extract(raw_response));

  if (response.response === "error" && response.error instanceof PbError) {
    dprint(`Got an error: '${print_error(response.error)}'`);
    throw response.error;
  }

  return response;
}

export class Model {

  public static async load_model_from_url(url: URL, type: ModelType):
    Promise<Model> {
    const model = new PbModel({
      type,
      url: new PbModel.FromURL({ url }),
    });

    return await Model.load_model(model);
  }

  public static async load_model_from_bytes(data: Uint8Array, type: ModelType):
    Promise<Model> {
    const model = new PbModel({
      data: new PbModel.FromBytes({ data }),
      type,
    });

    return await Model.load_model(model);
  }

  private static async load_model(model: PbModel): Promise<Model> {
    const response: ModelResp = await proto_request(
      "/api/load_model",
      new ModelReq({ model }),
      { encode: ModelReq.encode, decode: ModelResp.decode },
    );

    if (response.response === "handle" && response.handle instanceof Handle) {
      const handle = response.handle;
      dprint(`Loaded new model: ${handle}.`);

      return new Model(handle);
    } else {
      throw Error(
        "Invalid Response; expected a handle or an error, but got: " +
        `${response.response}'`,
      );
    }
  }

  // public static MnistModel = new Model(new Handle({ id: 0 }));
  // public static MobileNetFloatModel = new Model(new Handle({ id: 1 }));
  // public static MobileNetQuantModel = new Model(new Handle({ id: 2 }));
  public handle: Handle;

  private constructor(handle: Handle) {
    this.handle = handle;
  }

  public async predict_with_metrics(tensor: TfJsTensor):
    Promise<[TfJsTensor, Metrics]> {
    const request: InfReq = new InfReq({
      handle: this.handle,
      tensor: await tfjs_to_pb_tensor(tensor),
    });

    const response: InfResp = await proto_request(
      "/api/inference",
      request,
      { encode: InfReq.encode, decode: InfResp.decode },
    );

    if (response.response === "tensor" && response.tensor instanceof PbTensor) {
      if (!(response.metrics instanceof PbMetrics)) {
        throw Error(`No Metrics in response.`);
      }

      const metrics: Metrics = Metrics.from(response.metrics);
      dprint(`Took ${metrics.time_to_execute} μs.`);

      return [pb_to_tfjs_tensor(response.tensor), metrics];
    } else {
      throw Error(
        "Invalid Response; expected a tensor or an error, but got: " +
        `'${response.response}'`,
      );
    }
  }

  public async predict(tensor: TfJsTensor): Promise<TfJsTensor> {
    return (await this.predict_with_metrics(tensor))[0];
  }
}

// TODO: remove!! (after model loading works)
// export const MnistModel = Model.MnistModel;
// export const MobileNetFloatModel = Model.MobileNetFloatModel;
// export const MobileNetQuantModel = Model.MobileNetQuantModel;
