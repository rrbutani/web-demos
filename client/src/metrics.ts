import { inference } from "inference_proto";

import PbMetrics = inference.Metrics;

export class Metrics {

  public static from(metrics: PbMetrics): Metrics {
    return new Metrics(metrics.time_to_execute as number);
  }

  public time_to_execute: number; // in microseconds

  private constructor(time_to_execute: number) {
    this.time_to_execute = time_to_execute;
    // TODO: trace
  }
}
