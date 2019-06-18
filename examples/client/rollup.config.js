
import pkg from './package.json'

import typescript from 'rollup-plugin-typescript2'
import resolve from 'rollup-plugin-node-resolve';
import builtins from 'rollup-plugin-node-builtins';

export default
{ input: 'src/index.ts'
, output:
  [ { file: pkg.browser
    , format: 'umd'
    , name: pkg.name
    }
  , { file: pkg.module
    , format: 'es'
    }
  ]
, external:
  [ // Use _our_ versions of typescript and friends:
  , ...Object.keys(pkg.dependencies || {})
  , ...Object.keys(pkg.peerDependencies || {})
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
    })
  , typescript({ typescript: require('typescript') })
  ]
}