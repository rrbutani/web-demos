/**
 * Based on `mobilenet.ts`; modified for use with the web-demos-client.
 */

import * as tf from '@tensorflow/tfjs-core';

import {BaseModel, PoseNetOutputStride} from './posenet_model';

import { Model } from 'client';


function toFloatIfInt(input: tf.Tensor3D): tf.Tensor3D {
  return tf.tidy(() => {
    if (input.dtype === 'int32') input = input.toFloat();
    // Normalize the pixels [0, 255] to be between [-1, 1].
    input = tf.div(input, 127.5);
    return tf.sub(input, 1.0);
  })
}

export class MobileNetTFLite implements BaseModel {
  readonly model: Model
  readonly outputStride: PoseNetOutputStride

  constructor(model: Model, outputStride: PoseNetOutputStride) {
    this.model = model;
    this.outputStride = outputStride;
  }

  async predict(input: tf.Tensor3D): Promise<{[key: string]: tf.Tensor3D}> {
    // return tf.tidy(() => {
      const asFloat = toFloatIfInt(input);
      const asBatch = asFloat.expandDims(0);
      const res = await this.model.predict(asBatch);

      const [heatmaps4d, offsets4d, displacementFwd4d, displacementBwd4d] =
          res as tf.Tensor<tf.Rank>[];

      const heatmaps = heatmaps4d.squeeze() as tf.Tensor3D;
      const heatmapScores = heatmaps.sigmoid();
      const offsets = offsets4d.squeeze() as tf.Tensor3D;
      const displacementFwd = displacementFwd4d.squeeze() as tf.Tensor3D;
      const displacementBwd = displacementBwd4d.squeeze() as tf.Tensor3D;

      return {
        heatmapScores, offsets: offsets as tf.Tensor3D,
            displacementFwd: displacementFwd as tf.Tensor3D,
            displacementBwd: displacementBwd as tf.Tensor3D
      }
    // });
  }

  dispose() {}
}
