import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
  },
  {
    // eslint-plugin-react-hooks v7 adds a React-Compiler-oriented advisory rule,
    // `set-state-in-effect`, that flags the canonical data-fetching effect
    // pattern (set "loading" -> await -> set data) used by our hand-rolled
    // hooks layer (useResource / useFeed). That pattern is documented and
    // correct here, so we disable just this one advisory rule. Every other
    // react-hooks rule — rules-of-hooks, exhaustive-deps, and refs — stays on.
    files: ['**/*.{ts,tsx}'],
    rules: {
      'react-hooks/set-state-in-effect': 'off',
    },
  },
])
