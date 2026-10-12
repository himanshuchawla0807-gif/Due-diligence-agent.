import js from '@eslint/js';
import parser from '@typescript-eslint/parser';
import tsPlugin from '@typescript-eslint/eslint-plugin';
import hooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
export default [
  { ignores: ['dist/**', 'node_modules/**'] },
  { files: ['src/**/*.{ts,tsx}'], languageOptions: { parser, globals: globals.browser, parserOptions: { ecmaFeatures: { jsx: true } } },
    plugins: { '@typescript-eslint': tsPlugin, 'react-hooks': hooks },
    rules: { ...js.configs.recommended.rules, ...tsPlugin.configs.recommended.rules,
      'no-unused-vars': 'off', '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-undef': 'off', 'no-redeclare': 'off', '@typescript-eslint/no-explicit-any': 'warn',
      'react-hooks/rules-of-hooks': 'error', 'react-hooks/exhaustive-deps': 'warn' } },
];
