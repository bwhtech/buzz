import { register } from "node:module"

// Vite resolves `~icons/*` to components; node has no such package, so tests get an empty one.
register("./stubIconsHooks.mjs", import.meta.url)
