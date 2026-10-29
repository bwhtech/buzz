// Written out in full so the icon classes are generated at build time.
const ICONS: Record<string, string> = {
	mic: "lucide-mic",
	wrench: "lucide-wrench",
	coffee: "lucide-coffee",
	utensils: "lucide-utensils",
	users: "lucide-users",
	"clipboard-list": "lucide-clipboard-list",
	music: "lucide-music",
	"message-square": "lucide-message-square",
	pencil: "lucide-pencil",
}

export const scheduleIcon = (name: string | null | undefined) =>
	ICONS[name ?? ""] ?? "lucide-calendar-clock"
