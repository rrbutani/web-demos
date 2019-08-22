/**
 * @license
 * Copyright 2018 Google LLC. All Rights Reserved.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 * =============================================================================
 */

import * as tf from '@tensorflow/tfjs-core';

import {CLASSES} from './classes';

import { Model, ModelType } from 'client';

const BASE_PATH = 'https://storage.googleapis.com/tfjs-models/savedmodel/';

export {version} from './version';

export type ObjectDetectionBaseModel =
    'mobilenet_v1'|'mobilenet_v2'|'lite_mobilenet_v2'|'mobilenet_v1_habana'|
    'resnet_fpn';

export interface DetectedObject {
  bbox: [number, number, number, number];  // [x, y, width, height]
  class: string;
  score: number;
}

/**
 * Coco-ssd model loading is configurable using the following config dictionary.
 *
 * `base`: ObjectDetectionBaseModel. It determines wich PoseNet architecture
 * to load. The supported architectures are: 'mobilenet_v1', 'mobilenet_v2',
 * 'lite_mobilenet_v2', 'mobilenet_v1_habana', and 'resnet_fpn'. It defaults to
 * 'mobilenet_v1_habana'.
 *
 * `modelUrl`: An optional string that specifies custom url of the model. This
 * is useful for area/countries that don't have access to the model hosted on
 * GCP.
 */
export interface ModelConfig {
  base?: ObjectDetectionBaseModel;
  modelUrl?: string;
}

export async function load(config: ModelConfig = {}) {
  if (tf == null) {
    throw new Error(
        `Cannot find TensorFlow.js. If you are using a <script> tag, please ` +
        `also include @tensorflow/tfjs on the page before using this model.`);
  }
  const base = config.base || 'mobilenet_v1_habana';
  const modelUrl = config.modelUrl;
  if (['mobilenet_v1', 'mobilenet_v2', 'lite_mobilenet_v2',
      'mobilenet_v1_habana', 'resnet_fpn'].indexOf(base) ===
      -1) {
    throw new Error(
        `ObjectDetection constructed with invalid base model ` +
        `${base}. Valid names are 'mobilenet_v1', 'mobilenet_v2', ` +
        `'lite_mobilenet_v2', 'mobilenet_v1_habana', and 'resnet_fpn'.`);
  }

  const objectDetection = new ObjectDetection(base, modelUrl);
  await objectDetection.load();

  console.log("Model loaded!");
  return objectDetection;
}

export class ObjectDetection {
  private modelUrl: string;
  private modelFile: string;
  private imageSize: [number, number];
  private model: Model;

  constructor(base: ObjectDetectionBaseModel, modelUrl?: string) {
    this.modelUrl =
        modelUrl || `${BASE_PATH}${this.getPrefix(base)}/model.json`;

    this.modelFile = this.getBuiltInFileName(base);
    this.imageSize = this.getTargetImageSize(base);
  }

  private getPrefix(base: ObjectDetectionBaseModel) {
    return base === 'lite_mobilenet_v2' ? `ssd${base}` : `ssd_${base}`;
  }

  private getBuiltInFileName(base: ObjectDetectionBaseModel): string {
    switch (base) {
      case 'mobilenet_v1': return "ssd_mobilenet_v1_quantized_coco.tflite";
      case 'mobilenet_v2': return "ssd_mobilenet_v2_quantized_coco.tflite";
      case 'lite_mobilenet_v2': return "ssdlite_mobilenet_v2_coco.tflite";
      case 'mobilenet_v1_habana':
        return "ssd_mobilenet_v1_quantized_coco_habana.tflite";
      case 'resnet_fpn': return "ssd_resnet_50_fpn_coco.tflite";
      default:
        return exhaust(base);
    }
  }

  private getTargetImageSize(base: ObjectDetectionBaseModel): [number, number] {
    switch (base) {
      case 'mobilenet_v1':
      case 'mobilenet_v2':
      case 'lite_mobilenet_v2':
      case 'mobilenet_v1_habana':
        return [300, 300];
      case 'resnet_fpn':
        return [640, 640];
      default:
        return exhaust(base);
    }
  }

  async load() {
    try {
      this.model = await Model.load_model_from_url(
          this.modelUrl, ModelType.TFJS_GRAPH);
    } catch (err) {
      console.log(`Failed to convert model from URL (${this.modelUrl}); got: `
          + `error: ${err.kind}, ${err.message}.`);
      console.log(`Trying a built in model file now... (${this.modelFile})`);

      this.model = await Model.load_model_from_file(
            this.modelFile, ModelType.TFLITE_FLAT_BUFFER);
    }

    // Warmup the model.
    const result = await this.model.predict(
      tf.zeros([1, ...this.imageSize, 3]).asType('int32')) as tf.Tensor[];
    result.map(async (t) => await t.data());
    result.map(async (t) => t.dispose());
  }

  /**
   * Infers through the model.
   *
   * @param img The image to classify. Can be a tensor or a DOM element image,
   * video, or canvas.
   * @param maxNumBoxes The maximum number of bounding boxes of detected
   * objects. There can be multiple objects of the same class, but at different
   * locations. Defaults to 20.
   */
  private async infer(
      img: tf.Tensor3D|ImageData|HTMLImageElement|HTMLCanvasElement|
      HTMLVideoElement,
      _maxNumBoxes = 20): Promise<DetectedObject[]> {
    let height, width;

    const batched = tf.tidy(() => {
      if (!(img instanceof tf.Tensor)) {
        img = tf.browser.fromPixels(img);
      }

      height = img.shape[0];
      width = img.shape[1];

      // Reshape to a single-element batch so we can pass it to executeAsync.
      img = tf.image.resizeBilinear(img, this.imageSize);
      console.log(`resizing to ${this.imageSize}...`);
      return img.expandDims(0);
    });

    console.log(`batched: ${batched}`);

    console.log(`height: ${height}, width: ${width}`);

    // model returns two tensors:
    // 1. box classification score with shape of [1, 1917, 90]
    // 2. box location with shape of [1, 1917, 1, 4]
    // where 1917 is the number of box detectors, 90 is the number of classes.
    // and 4 is the four coordinates of the box.
    const batchedResult = await this.model.predict(batched) as tf.Tensor[];

    const boxes = batchedResult[0].dataSync() as Float32Array;
    const classes = batchedResult[1].dataSync() as Float32Array;
    const scores = batchedResult[2].dataSync() as Float32Array;
    const numDetections = batchedResult[3].dataSync() as Float32Array;

    console.log(boxes);
    console.log(scores);
    console.log(classes);
    console.log(numDetections);

    // clean the webgl tensors
    batched.dispose();
    tf.dispose(batchedResult);

    return this.buildDetectedObjects(width, height, boxes, Array.from(scores),
      numDetections[0], Array.from(classes));
  }

  private buildDetectedObjects(
      width: number, height: number, boxes: Float32Array, scores: number[],
      numDetections: number, classes: number[]): DetectedObject[] {
    const count = numDetections;
    const objects: DetectedObject[] = [];

    for (let i = 0; i < count; i++) {
      const bbox = Array(4);
      const minY = boxes[4 * i + 0] * height;
      const minX = boxes[4 * i + 1] * width;
      const maxY = boxes[4 * i + 2] * height;
      const maxX = boxes[4 * i + 3] * width;
      bbox[0] = minX;
      bbox[1] = minY;
      bbox[2] = maxX - minX;
      bbox[3] = maxY - minY;
      objects.push({
        bbox: bbox as [number, number, number, number],
        class: CLASSES[classes[i] + 1].displayName,
        score: scores[i]
      });
    }
    return objects;
  }

  /**
   * Detect objects for an image returning a list of bounding boxes with
   * assocated class and score.
   *
   * @param img The image to detect objects from. Can be a tensor or a DOM
   *     element image, video, or canvas.
   * @param maxNumBoxes The maximum number of bounding boxes of detected
   * objects. There can be multiple objects of the same class, but at different
   * locations. Defaults to 20.
   *
   */
  async detect(
      img: tf.Tensor3D|ImageData|HTMLImageElement|HTMLCanvasElement|
      HTMLVideoElement,
      maxNumBoxes = 20): Promise<DetectedObject[]> {
    return this.infer(img, maxNumBoxes);
  }

  /**
   * Dispose the tensors allocated by the model. You should call this when you
   * are done with the model.
   */
  dispose() {
    // if (this.model) {
    //   this.model.dispose();
    // }
  }
}

function exhaust(_: never): never {
  // tslint:disable-next-line:no-console
  console.log("if you're seeing this something has gone very very wrong...");

  while (true) { }
}
