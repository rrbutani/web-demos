
import pkg from './package.json'

import typescript from 'rollup-plugin-typescript2'
import resolve from 'rollup-plugin-node-resolve';
import builtins from 'rollup-plugin-node-builtins';
import commonJS from 'rollup-plugin-commonjs'

export default
{ input: 'src/index.ts'
, output:
  [ { file: pkg.browser
    , format: 'umd'
    , name: pkg.name
    , globals:
      { 'protobufjs/minimal': 'protobuf' }
    }
  , { file: pkg.module
    , format: 'es'
    }
  ]
, external:
  [ // Use _our_ versions of typescript and friends:
  , ...Object.keys(pkg.dependencies || {})
  , ...Object.keys(pkg.peerDependencies || {})
  , "protobufjs/minimal" // Users will have to add a script tag for:
  // '//cdn.rawgit.com/dcodeIO/protobuf.js/6.8.8/dist/minimal/protobuf.min.js'
  ]
, plugins:
  [ builtins()
  , resolve(
    { "mainFields":
      [ "module"
      , "browser"
      ]
    , "extensions":
      [ ".js"
      , ".json"
      , ".mjs"
      , ".cjs"
      , ".jsx"
      ]
    }),
  , commonJS({ include: 'node_modules/**' })
  , typescript({ typescript: require('typescript') })
  ]
}