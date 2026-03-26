---
topic: eslint-v9-flat-config
date: 2026-03-26
tags: [eslint, linting, javascript, tooling]
---

# ESLint v9 Flat Config

## What I Learned

ESLint v9 introduced a new configuration system called "flat config" — a breaking change from the old `.eslintrc` format.

### The engine/rules split

ESLint itself (`eslint`) is just the engine — it runs files through rules and reports errors. It ships with no rules enabled by default. Rules come from separate plugins.

`@eslint/js` is the official plugin that provides the standard ruleset. It exposes `js.configs.recommended` — the baseline set of rules most projects use (no undeclared variables, no unreachable code, etc.).

This split is intentional: the engine is language-agnostic. There are now official plugins for CSS (`@eslint/css`), JSON (`@eslint/json`), and Markdown too.

### eslint.config.js

The flat config is a JS file that exports an array of config objects. Each object applies to a set of files and can specify rules, plugins, and settings:

```js
import js from "@eslint/js";

export default [
  js.configs.recommended,
  {
    files: ["**/*.js"],
  },
];
```

Objects are applied in order — later ones override earlier ones. There's no magic, no hidden behaviour.

### The `"type": "module"` requirement

`eslint.config.js` uses `import`/`export` (ES module syntax). Node defaults to treating `.js` files as CommonJS (`require`/`module.exports`). Adding `"type": "module"` to `package.json` tells Node to treat all `.js` files in the project as ES modules, eliminating a reparsing warning and performance overhead.

### Old vs new syntax

A lot of tutorials and Stack Overflow answers are still written for ESLint v8. If examples use `.eslintrc.json` or `extends: ['eslint:recommended']` as a string in an array, that's v8 — it won't work in v9.

## Why It Matters

ESLint is the standard JS linter across the industry. Understanding the flat config system means you can read and write configs for any modern project without copy-pasting blindly. Knowing the engine/rules split also explains why ESLint is evolving toward being a universal linter — relevant as `@eslint/css` matures.

## Key Takeaways

- `eslint` is the engine; rules come from separate plugins like `@eslint/js`
- Flat config (`eslint.config.js`) exports an array — each item is a config object applied in order
- `"type": "module"` in `package.json` is required when using `import`/`export` in config files
- v8 syntax (`.eslintrc`, `extends` as string array) does not work in v9 — watch for this in tutorials

## Resources

- [ESLint flat config docs](https://eslint.org/docs/latest/use/configure/configuration-files)
- [@eslint/js on npm](https://www.npmjs.com/package/@eslint/js)

## Questions Still Open

- When does it make sense to add `@eslint/css` alongside or instead of Stylelint? (tracked in issue #14)
