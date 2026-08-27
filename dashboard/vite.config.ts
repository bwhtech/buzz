import path from "node:path"

import vue from "@vitejs/plugin-vue"
import frappeui from "frappe-ui/vite"
import { defineConfig } from "vite"

export default defineConfig({
	plugins: [
		frappeui({
			frappeProxy: {
				port: 8080,
				source: "^/(app|login|api|assets|files|private|razorpay_checkout|events)",
			},
			jinjaBootData: true,
			lucideIcons: true,
			buildConfig: {
				indexHtmlPath: "../buzz/www/dashboard.html",
				emptyOutDir: true,
				sourcemap: true,
				outDir: "../buzz/public/dashboard",
				chunkSizeWarningLimit: 1500,
				target: "es2015",
			},
		}),
		vue(),
	],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
			"tailwind.config.js": path.resolve(__dirname, "tailwind.config.js"),
		},
	},
	optimizeDeps: {
		// Pre-bundling gives frappe-ui and frappe-ui/editor their own ProseMirror
		// copy each, so the editor throws on "gapcursor". resolve.dedupe does not
		// merge them.
		exclude: ["frappe-ui"],
		// frappe-ui is not pre-bundled, so its nested CJS feather-icons needs
		// pre-bundling of its own for default-export interop.
		include: ["feather-icons", "frappe-ui > feather-icons"],
	},
	server: {
		allowedHosts: true,
	},
})
