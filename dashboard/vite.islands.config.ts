// Vue components mounted on Jinja pages. A build of its own, apart from the SPA.
import path from "node:path"

import vue from "@vitejs/plugin-vue"
import autoprefixer from "autoprefixer"
import frappeui from "frappe-ui/vite"
import { lucideIconsPlugin } from "frappe-ui/vite/lucideIconsPlugin"
import tailwindcss from "tailwindcss"
import { defineConfig } from "vite"

export default defineConfig({
	plugins: [
		// The icon resolver alone: lucideIcons' auto-import would rewrite the SPA's components.d.ts.
		frappeui({ frappeProxy: false, jinjaBootData: false, buildConfig: false, lucideIcons: false }),
		lucideIconsPlugin(),
		vue(),
	],
	base: "/assets/buzz/islands/",
	// The SPA's public/ folder (favicon and the like) has no place here.
	publicDir: false,
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
			"@public": path.resolve(__dirname, "../buzz/public"),
			"tailwind.config.js": path.resolve(__dirname, "tailwind.config.js"),
			// frappe-ui's Button imports RouterLink for its `route` prop; islands never route.
			"vue-router": path.resolve(__dirname, "src/islands/routerStub.ts"),
		},
	},
	css: {
		postcss: {
			plugins: [tailwindcss({ config: "./tailwind.islands.config.js" }), autoprefixer()],
		},
	},
	build: {
		outDir: "../buzz/public/islands",
		emptyOutDir: true,
		manifest: true,
		rollupOptions: { input: { islands: path.resolve(__dirname, "src/islands/main.ts") } },
	},
})
