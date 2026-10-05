// The first icon is the default for a new link, so it leads the picker.
export const LINK_ICONS = [
	{ value: "link", label: "Link", icon: "lucide-link" },
	{ value: "globe", label: "Website", icon: "lucide-globe" },
	{ value: "map-pin", label: "Map", icon: "lucide-map-pin" },
	{ value: "video", label: "Live stream", icon: "lucide-video" },
	{ value: "presentation", label: "Slides", icon: "lucide-presentation" },
	{ value: "file-text", label: "Document", icon: "lucide-file-text" },
	{ value: "message-circle", label: "Community", icon: "lucide-message-circle" },
	{ value: "calendar", label: "Calendar", icon: "lucide-calendar" },
	{ value: "book-open", label: "Guide", icon: "lucide-book-open" },
	{ value: "folder-git-2", label: "Repository", icon: "lucide-folder-git-2" },
	{ value: "circle-play", label: "Recording", icon: "lucide-circle-play" },
	{ value: "users", label: "Social", icon: "lucide-users" },
	{ value: "camera", label: "Photos", icon: "lucide-camera" },
	{ value: "clipboard-list", label: "Form", icon: "lucide-clipboard-list" },
]

export function linkIconClass(icon: string | null) {
	return LINK_ICONS.find((option) => option.value === icon)?.icon ?? "lucide-link"
}

export function normalizeUrl(raw: string) {
	const text = raw.trim()
	return /^https?:\/\//i.test(text) ? text : `https://${text}`
}

export function isValidUrl(raw: string) {
	const text = raw.trim()
	if (!text || /\s/.test(text)) return false
	try {
		return new URL(normalizeUrl(text)).hostname.includes(".")
	} catch {
		return false
	}
}

export function hostOf(url: string) {
	try {
		return new URL(normalizeUrl(url)).hostname.replace(/^www\./, "")
	} catch {
		return url
	}
}
