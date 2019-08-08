#!/usr/bin/env node

/**
 * Small script that uses `node-coveralls` to convert lcov files.
 */

import { convertLcovToCoveralls } from "coveralls";

import { argv } from "process";

const input_lcov_file: string =
  argv.filter((arg: string) => arg.endsWith(".lcov"))[0];

const output_coveralls_file: string =
  argv.filter((arg: string) => arg.endsWith(".json"))[0];

if (typeof input_lcov_file !== "string" ||
  typeof output_coveralls_file !== "string") {
  throw new Error("Invalid arguments. Expected: <lcov file> <json file> [root");
}
