const DEBUG_ENV_VAR: string = "debug_env_value_here";

export function dprint(p: string) {
  if (DEBUG_ENV_VAR === "true") {
    // tslint:disable-next-line:no-console
    console.log(p);
  }
}

export function exhaust(_: never): never {
  // tslint:disable-next-line:no-console
  console.log("if you're seeing this something has gone very very wrong...");

  while (true) { }
}
