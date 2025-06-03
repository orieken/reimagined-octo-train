import globals from 'globals';
import pluginJs from '@eslint/js';
import tseslint from 'typescript-eslint';
/* eslint-disable */

/** @type {import('eslint').Linter.Config[]} */
export default [
  { files: ['**/*.{ts}'] },
  { languageOptions: { globals: globals.browser } },
  pluginJs.configs.recommended,
  ...tseslint.configs.recommended,
  {
    rules: {
      '@typescript-eslint/naming-convention': [
        'error',
        {
          selector: 'default',
          format: ['camelCase', 'PascalCase'],
          leadingUnderscore: 'forbid',
          trailingUnderscore: 'forbid',
        },
        {
          selector: 'class',
          format: ['PascalCase'],
        },
        {
          selector: 'interface',
          format: ['PascalCase'],
        },
        {
          selector: 'typeLike',
          format: ['UPPER_CASE', 'PascalCase'],
        },
        {
          selector: 'parameter',
          format: ['camelCase'],
          leadingUnderscore: 'allow',
        },
      ],
      complexity: [
        'error',
        {
          max: 5,
        },
      ],
      'max-classes-per-file': ['error', 1],
      'max-len': [
        'error',
        {
          ignorePattern: '^import [^,]+ from |^export | implements | (\'|")(http|https):',
          code: 140,
        },
      ],
      'max-params': ['error', 3],
      'spaced-comment': ['error', 'always', { markers: ['/'] }],
      'comma-dangle': ['error', 'only-multiline'],
      'no-unused-vars': [
        'error',
        {
          varsIgnorePattern: '^_',
          argsIgnorePattern: '^_',
        },
      ],
    },
  },
];
