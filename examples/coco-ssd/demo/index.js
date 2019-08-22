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

import * as cocoSsd from '@tensorflow-models/coco-ssd';

import imageURL from './image1.jpg';
import image2URL from './image2.jpg';

let model;

const image_div = document.getElementById('uploaded-images');
const end_div = document.getElementById('end');

const max_width = window.innerWidth * 4.0 / 9.0;
const max_height = window.innerHeight * 2.0 / 3.0;
// let baseModel = 'lite_mobilenet_v2';

window.onload = async () => model = await cocoSsd.load();

const button = document.getElementById('toggle');
button.onclick = () => {
  image.src = image.src.endsWith(imageURL) ? image2URL : imageURL;
};

const select = document.getElementById('base_model');
select.onchange = async (event) => {
  model.dispose();
  model = await cocoSsd.load(
      {base: event.srcElement.options[event.srcElement.selectedIndex].value});
  console.log('model loaded');
};

const image = document.getElementById('image');
image.src = imageURL;
// image.width = 300; // TODO
// image.height = 300; // TODO

async function single_image(image, canvas) {
  console.time('predict1');
  const result = await model.detect(image);
  console.timeEnd('predict1');

  const c = canvas;
  c.width = image.width;
  c.height = image.height;

  const context = c.getContext('2d');
  context.drawImage(image, 0, 0, c.width, c.height);
  context.font = '10px Arial';

  console.log('number of detections: ', result.length);
  for (let i = 0; i < result.length; i++) {
    context.beginPath();
    context.rect(...result[i].bbox);
    context.lineWidth = 1;
    context.strokeStyle = 'green';
    context.fillStyle = 'green';
    context.stroke();
    context.fillText(
        result[i].score.toFixed(3) + ' ' + result[i].class, result[i].bbox[0],
        result[i].bbox[1] > 10 ? result[i].bbox[1] - 5 : 10);
  }
}

const runButton = document.getElementById('run');
runButton.onclick = async () => {
  await single_image(image, document.getElementById('canvas'))
};

const filesElement = document.getElementById('files');
filesElement.addEventListener('change', evt => {
  let files = evt.target.files;
  // Display thumbnails & issue call to predict each image.
  for (let i = 0, f; f = files[i]; i++) {
    // Only process image files (skip non image files)
    if (!f.type.match('image.*')) {
      continue;
    }
    let reader = new FileReader();
    const idx = i;
    // Closure to capture the file information.
    reader.onload = e => {
      // Fill the image & call predict.
      let div = document.createElement('div');
      let img = document.createElement('img');
      let can = document.createElement('canvas');

      div.appendChild(img);
      div.appendChild(can);

      image_div.insertBefore(div, end_div.nextSibling);

      img.src = e.target.result;
      img.onload = () => {
        if (img.width > max_width) {
          img.height *= (max_width / img.width);
          img.width = max_width;
        }

        if (img.height > max_height) {
          img.width *= (max_height / img.height);
          img.height = max_height;
        }
        single_image(img, can)
      };
    };

    // Read in the image file as a data URL.
    reader.readAsDataURL(f);
  }
});
