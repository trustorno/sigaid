import typescript from '@rollup/plugin-typescript';
import { terser } from 'rollup-plugin-terser';

export default [
  // UMD build (for script tag)
  {
    input: 'src/widget.ts',
    output: {
      file: 'dist/widget.js',
      format: 'umd',
      name: 'SigAid',
      sourcemap: true,
    },
    plugins: [
      typescript({ tsconfig: './tsconfig.json' }),
    ],
  },
  // Minified UMD build
  {
    input: 'src/widget.ts',
    output: {
      file: 'dist/widget.min.js',
      format: 'umd',
      name: 'SigAid',
      sourcemap: true,
    },
    plugins: [
      typescript({ tsconfig: './tsconfig.json' }),
      terser(),
    ],
  },
  // ESM build (for bundlers)
  {
    input: 'src/widget.ts',
    output: {
      file: 'dist/widget.esm.js',
      format: 'esm',
      sourcemap: true,
    },
    plugins: [
      typescript({ tsconfig: './tsconfig.json' }),
    ],
  },
];
