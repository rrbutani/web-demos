#!/usr/bin/env node

/**
 * Quick and simple script that builds the protobuf messages.
 */

import { dirname } from 'path';
import { mkdirSync as mkdir, existsSync as exists } from 'fs';

import { pbjs, pbts } from 'protobufjs/cli';

import pkg from './../package.json';

const config = pkg.config;

const message_dir = config.message_dir || "messages";
const message_file = config.message_file || "build/messages.js";
const message_types = config.message_types || "build/types/messages.d.ts";

const throw_err = (err: Error, _: string) => { if (err) throw err; }
const create = (file: string) => {
  const path = dirname(file);
  exists(path) || mkdir(dirname(file), { "recursive": true });
}

create(message_file)
create(message_types)

pbjs.main(
  [ "--target"
  , "static-module"
  , "--wrap"
  , "es6"
  , "--es6"
  , "--keep-case"
  , "--path"
  , message_dir
  , "--out"
  , message_file
  , `${message_dir}/*.proto`
  ]
, throw_err
);

pbts.main(
  [ message_file
  , "--out"
  , message_types
  ]
, throw_err
)
