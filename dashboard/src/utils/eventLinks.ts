export const LINK_ICONS = [
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
	{ value: "link", label: "Link", icon: "lucide-link" },
]

const SUGGESTIONS: [RegExp, string, string][] = [
	[/github\.com|gitlab\.com/, "folder-git-2", "Repository"],
	[/youtube\.com|youtu\.be|vimeo\.com/, "circle-play", "Watch the recording"],
	[/linkedin\.com|x\.com|twitter\.com|instagram\.com/, "users", "Follow us"],
	[/maps\.app\.goo\.gl|google\.[a-z.]+\/maps|goo\.gl\/maps/, "map-pin", "Venue on Google Maps"],
	[/docs\.google\.com\/presentation|speakerdeck|slideshare/, "presentation", "Slides"],
	[/docs\.google\.com\/forms|forms\.gle|typeform/, "clipboard-list", "Form"],
	[/docs\.google|notion\.(so|site)/, "file-text", "Event notes"],
	[/discord|t\.me|telegram|chat\.whatsapp|slack\.com/, "message-circle", "Community chat"],
	[/zoom\.us|meet\.google|teams\.microsoft/, "video", "Join online"],
	[/photos\.google|photos\.app\.goo\.gl|flickr/, "camera", "Event photos"],
	[/lu\.ma|calendar/, "calendar", "Add to calendar"],
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

export function suggestLink(raw: string): { icon: string; label: string } | null {
	if (!isValidUrl(raw)) return null
	const url = normalizeUrl(raw)
	const match = SUGGESTIONS.find(([pattern]) => pattern.test(url))
	return match ? { icon: match[1], label: match[2] } : { icon: "globe", label: hostOf(url) }
}
