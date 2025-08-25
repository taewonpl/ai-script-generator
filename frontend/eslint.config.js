import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import unusedImports from 'eslint-plugin-unused-imports'
import importPlugin from 'eslint-plugin-import'
import { globalIgnores } from 'eslint/config'
import gridLayoutQuality from './eslint-rules/grid-layout-quality.js'

export default tseslint.config([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    plugins: {
      'grid-layout-quality': gridLayoutQuality,
      'unused-imports': unusedImports,
      import: importPlugin,
    },
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    settings: {
      'import/resolver': {
        typescript: {
          alwaysTryTypes: true,
          project: './tsconfig.app.json',
        },
      },
    },
    rules: {
      // Auto-fix imports and unused variables
      '@typescript-eslint/consistent-type-imports': [
        'error',
        {
          prefer: 'type-imports',
          fixStyle: 'separate-type-imports',
        },
      ],
      'unused-imports/no-unused-imports': 'error',
      'unused-imports/no-unused-vars': [
        'error',
        {
          vars: 'all',
          varsIgnorePattern: '^_',
          args: 'after-used',
          argsIgnorePattern: '^_',
          ignoreRestSiblings: true,
        },
      ],
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          ignoreRestSiblings: true,
        },
      ],
      '@typescript-eslint/no-explicit-any': ['warn', { ignoreRestArgs: true }],

      // Security: Prevent process.env usage in client code
      'no-restricted-globals': [
        'error',
        {
          name: 'process',
          message:
            'Use import.meta.env instead of process.env in client code. process.env is only available in Node.js environments like vite.config.ts',
        },
      ],
      // Additional environment variable security
      'no-restricted-syntax': [
        'error',
        {
          selector:
            'MemberExpression[object.name="process"][property.name="env"]',
          message:
            'Use import.meta.env instead of process.env in client code. Environment variables with VITE_ prefix are automatically available via import.meta.env',
        },
        // Grid Layout Quality Rules
        {
          selector:
            'JSXElement[openingElement.name.name="Box"][openingElement.attributes/*/key.name="sx"] Property[key.name="gap"], JSXElement[openingElement.name.name="Stack"][openingElement.attributes/*/key.name="sx"] Property[key.name="gap"]',
          message:
            'Avoid using CSS gap in MUI components that have built-in spacing props. Use spacing prop instead for consistency: <Box spacing={2}> or <Stack spacing={2}>',
        },
        {
          selector:
            'JSXElement[openingElement.name.name="Grid"][openingElement.attributes/*/key.name="sx"] Property[key.name="gap"]',
          message:
            "Do not use CSS gap with MUI Grid containers. Use spacing prop instead: <Grid container spacing={2}>. CSS gap can conflict with Grid's negative margins.",
        },
        {
          selector:
            'JSXOpeningElement[name.name="Grid"][attributes/*/name.name="spacing"][attributes/*/value/expression/properties/*/key.name="gap"]',
          message:
            'Do not use both spacing prop and CSS gap simultaneously. This creates conflicting spacing behavior. Choose either spacing={2} OR sx={{gap: 2}}, not both.',
        },
      ],
      // Grid Quality and Best Practice Rules
      'no-restricted-properties': [
        'warn',
        {
          object: 'Grid',
          property: 'container',
          message:
            'Consider migrating to Grid2 for better performance and flexibility. Grid2 provides the same API with improved layout calculations.',
        },
      ],
      // Custom Grid validation rules
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: '@mui/material',
              importNames: ['Grid'],
              message: 'Use Grid2 from @mui/material/Grid2 instead',
            },
          ],
        },
      ],
      // Custom Grid Layout Quality Rules
      'grid-layout-quality/no-grid-gap-conflict': 'error',
      'grid-layout-quality/grid2-migration-warning': 'warn',
      'grid-layout-quality/grid-layout-validation': 'error',
    },
  },
  // Allow process.env in build and test configuration files
  {
    files: [
      'vite.config.ts',
      'vite.config.js',
      'rollup.config.*',
      'webpack.config.*',
      'playwright.config.*',
      '**/*.config.ts',
      '**/*.config.js',
      '**/tests/**',
      '**/test/**',
      '**/__tests__/**',
      '**/e2e/**',
    ],
    rules: {
      'no-restricted-globals': 'off',
      'no-restricted-syntax': 'off',
    },
  },
])
