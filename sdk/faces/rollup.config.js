import typescript from '@rollup/plugin-typescript';
import terser from '@rollup/plugin-terser';

export default [
  // ESM build
  {
    input: 'src/index.ts',
    output: {
      file: 'dist/index.esm.js',
      format: 'esm',
      sourcemap: true,
    },
    plugins: [
      typescript({ tsconfig: './tsconfig.json' }),
      terser(),
    ],
  },
  // CJS build
  {
    input: 'src/index.ts',
    output: {
      file: 'dist/index.js',
      format: 'cjs',
      sourcemap: true,
      exports: 'named',
    },
    plugins: [
      typescript({ tsconfig: './tsconfig.json' }),
      terser(),
    ],
  },
  // UMD build for browsers (standalone)
  {
    input: 'src/index.ts',
    output: {
      file: 'dist/sigaid-faces.umd.js',
      format: 'umd',
      name: 'SigAidFaces',
      sourcemap: true,
    },
    plugins: [
      typescript({ tsconfig: './tsconfig.json' }),
      terser(),
    ],
  },
];
