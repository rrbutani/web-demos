#!/usr/bin/env node

/**
 * Quick and simple script that builds the protobuf messages.
 */

import { existsSync as exists, mkdirSync as mkdir, writeFileSync as write_file } from "fs";
import { basename, dirname, join } from "path";
import { argv } from "process";

import { pbjs, pbts } from "protobufjs/cli";

import pkg from "./../package.json";

const config = pkg.config;

const message_build = config.message_build_folder || "build";
const message_types = config.message_types_folder || "build";

const messages_babelrc_config = {
  env:
  {
    test:
    {
      presets:
        [["@babel/preset-env"
          , { modules: "commonjs" },
        ],
        ],
    },
  },
};

const throw_err = (err: Error, _: string) => { if (err) { throw err; } };
const create = (file: string) => {
  const path = dirname(file);
  if (!exists(path)) { mkdir(dirname(file), { recursive: true }); }
};

const messages: string[] =
  argv.filter((arg: string) => arg.endsWith(".proto"));

messages.forEach((m) => {
  const message_js_file = join(message_build, basename(m, ".proto") + ".js");
  const message_typings = join(message_types, basename(m, ".proto") + ".d.ts");

  create(message_js_file);
  create(message_typings);

  pbjs.main(
    ["--target"
      , "static-module"
      , "--wrap"
      , "es6"
      , "--es6"
      , "--keep-case"
      , "--path"
      , dirname(m)
      , "--out"
      , message_js_file
      , m,
    ]
    , throw_err,
  );

  pbts.main(
    [message_js_file
      , "--out"
      , message_typings,
    ]
    , throw_err,
  );
});

write_file(
  join(message_build, ".babelrc"),
  JSON.stringify(messages_babelrc_config),
);
