import typescript from 'rollup-plugin-typescript2'

import pkg from './package.json'

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
  [ typescript({ typescript: require('typescript') }) ]
}