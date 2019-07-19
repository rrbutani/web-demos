import pkg from './package.json'

import typescript from 'rollup-plugin-typescript2'
import resolve from 'rollup-plugin-node-resolve';
import builtins from 'rollup-plugin-node-builtins';
import commonJS from 'rollup-plugin-commonjs'
import sourcemaps from 'rollup-plugin-sourcemaps';
import replace from 'rollup-plugin-replace';

export default
{ input: 'src/index.ts'
, output:
  [ { file: pkg.module
    , format: 'es'
    , name: pkg.name
    , sourcemap: true
    , globals:
      { '@tensorflow/tfjs-core': 'tf'
      , '@tensorflow/tfjs-data': 'tf.data'
      , '@tensorflow/tfjs-layers': 'tf'
      , '@tensorflow/tfjs-converter': 'tf'
      , '@tensorflow/tfjs-vis': 'tfvis'
      , '@tensorflow/tfjs': 'tf'
      }
    }
  ]
, external:
  [ // Use _our_ versions of typescript and friends:
  , ...Object.keys(pkg.dependencies || {})
  , ...Object.keys(pkg.peerDependencies || {})
  , '@tensorflow/tfjs-core'
  , '@tensorflow/tfjs-data'
  , '@tensorflow/tfjs-layers'
  , '@tensorflow/tfjs-converter'
  , '@tensorflow/tfjs-vis'
  , '@tensorflow/tfjs'
  ]
, plugins:
  [ replace({ debug_env_value_here: ("DEBUG" in process.env).toString() })
  , typescript({ typescript: require('typescript') })
  , builtins()
  , resolve(
    { mainFields:
      [ "module"
      , "browser"
      , "main"
      ]
    , extensions:
      [ ".js"
      , ".jsx"
      , ".json"
      , ".mjs"
      , ".cjs"
      , ".ts"
      , ".tsx"
      ]
    })
  , commonJS(
    { include: /node_modules/
    , namedExports:
      { 'node_modules/protobufjs/minimal.js':
          [ "Reader", "Writer", "util", "roots" ]
      }
    })
  , sourcemaps()
  ]
, onwarn: warning => {
  let {code} = warning;
    if (code === 'CIRCULAR_DEPENDENCY' || code === 'CIRCULAR' ||
        code === 'THIS_IS_UNDEFINED') {
      return;
    }
    console.warn('WARNING: ', warning.toString());
  }
}
