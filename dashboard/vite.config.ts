import path from "node:path"

import vue from "@vitejs/plugin-vue"
import frappeui from "frappe-ui/vite"
import { defineConfig } from "vite"

// Link previews read the served HTML, so a public form's page renders its own tags. Jinja runs
// only on the built page (buzz/www/dashboard.html); the dev server would show it as text.
const LINK_PREVIEW = `{% if link_preview %}<title>{{ link_preview.title | e }}</title>
    <meta name="description" content="{{ link_preview.description | e }}" />
    <meta property="og:title" content="{{ link_preview.title | e }}" />
    <meta property="og:description" content="{{ link_preview.description | e }}" />
    {% if link_preview.image %}<meta property="og:image" content="{{ link_preview.image | e }}" />{% endif %}
    {% else %}<title>Buzz Dashboard</title>{% endif %}`

const linkPreviewTags = {
	name: "buzz-link-preview-tags",
	apply: "build" as const,
	transformIndexHtml: (html: string) => html.replace("<title>Buzz Dashboard</title>", LINK_PREVIEW),
}

export default defineConfig({
	plugins: [
		linkPreviewTags,
		frappeui({
			frappeProxy: {
				port: 8080,
				source: "^/(app|login|api|assets|files|private|razorpay_checkout|events|community|u/)",
			},
			jinjaBootData: true,
			lucideIcons: true,
			buildConfig: {
				indexHtmlPath: "../buzz/www/dashboard.html",
				emptyOutDir: true,
				sourcemap: true,
				outDir: "../buzz/public/dashboard",
			},
		}),
		vue({
			// The event page's custom elements, shared with the dashboard.
			template: { compilerOptions: { isCustomElement: (tag) => tag === "event-countdown" } },
		}),
	],
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
			// TypeScript shared with the app's own bundles (bench build), e.g. the event banner.
			"@public": path.resolve(__dirname, "../buzz/public"),
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
		fs: { allow: [".", "../buzz/public/js"] },
	},
})
