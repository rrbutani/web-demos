import { Tensor as TfJsTensor } from "@tensorflow/tfjs";
import { fetch } from "cross-fetch";
import { Reader, Writer } from "protobufjs";

import { inference } from "inference_proto";

import { Metrics } from "./metrics";
import { pb_to_tfjs_tensors, tfjs_to_pb_tensors } from "./tensor";
import { dprint } from "./util";

import PbTensors = inference.Tensors;
import PbModel = inference.Model;
import ModelReq = inference.LoadModelRequest;
import ModelResp = inference.LoadModelResponse;
import InfReq = inference.InferenceRequest;
import InfResp = inference.InferenceResponse;
import Handle = inference.ModelHandle;
import PbError = inference.Error;
import PbMetrics = inference.Metrics;

export type ModelType = PbModel.Type;

const Type = PbModel.Type;
export { Type };

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
  "Accept": "application/x-protobuf",
  "Content-Type": "application/x-protobuf",
};

type URL = string; // TODO: this isn't great; it's a stop gap

interface PReq<Req, Resp> {
  encode(message: Req, writer?: Writer): Writer;
  decode(reader: (Reader | Uint8Array), length?: number): Resp;
}

interface PRsp {
  response?: string;
  error?: (inference.IError | null);
}

async function proto_request<Req, Rsp extends PRsp, W extends PReq<Req, Rsp>>(
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

  public static async load_model_from_file(file: string, type: ModelType):
    Promise<Model> {
    const model = new PbModel({
      file: new PbModel.FromFile({ file }),
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

  public handle: Handle;

  private constructor(handle: Handle) {
    this.handle = handle;
  }

  public async predict_with_metrics(tensor: TfJsTensor | TfJsTensor[]):
    Promise<[TfJsTensor | TfJsTensor[], Metrics]> {
    const request: InfReq = new InfReq({
      handle: this.handle,
      tensors: await tfjs_to_pb_tensors(tensor),
    });

    const response: InfResp = await proto_request(
      "/api/inference",
      request,
      { encode: InfReq.encode, decode: InfResp.decode },
    );

    if (response.response === "tensors" &&
      response.tensors instanceof PbTensors) {
      if (!(response.metrics instanceof PbMetrics)) {
        throw Error(`No Metrics in response.`);
      }

      const metrics: Metrics = Metrics.from(response.metrics);
      dprint(`Took ${metrics.time_to_execute} μs.`);

      return [pb_to_tfjs_tensors(response.tensors), metrics];
    } else {
      throw Error(
        "Invalid Response; expected a tensor or an error, but got: " +
        `'${response.response}'`,
      );
    }
  }

  public async predict(tensor: TfJsTensor | TfJsTensor[],
  ): Promise<TfJsTensor | TfJsTensor[]> {
    return (await this.predict_with_metrics(tensor))[0];
  }
}
