import path from "node:path";
import vue from "@vitejs/plugin-vue";
import frappeui from "frappe-ui/vite";
import { defineConfig } from "vite";

// https://vitejs.dev/config/
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
		// frappe-ui ships as source (its exports point at src/*.ts). Its files
		// import `~icons/lucide/*` virtuals that only the lucideIcons Vite plugin
		// can resolve, and use extensionless `#molecules/*` subpath imports that
		// esbuild cannot resolve, so it must skip esbuild pre-bundling and go
		// through the plugin pipeline instead.
		exclude: ["frappe-ui"],
		// frappe-ui bundles its own CJS feather-icons; since frappe-ui is not
		// pre-bundled, pre-bundle that nested copy so its default export gets
		// CJS->ESM interop (otherwise FeatherIcon import fails and the app never
		// mounts).
		include: ["feather-icons", "frappe-ui > feather-icons"],
	},
	server: {
		allowedHosts: true,
	},
});
