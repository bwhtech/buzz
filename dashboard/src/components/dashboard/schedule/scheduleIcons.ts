// Written out in full so the icon classes are generated at build time.
const ICONS: Record<string, string> = {
	mic: "lucide-mic",
	wrench: "lucide-wrench",
	coffee: "lucide-coffee",
	utensils: "lucide-utensils",
	users: "lucide-users",
	zap: "lucide-zap",
	"clipboard-list": "lucide-clipboard-list",
	"message-square": "lucide-message-square",
	"pen-line": "lucide-pen-line",
	"message-circle": "lucide-message-circle",
}

export const scheduleIcon = (name: string | null | undefined) => ICONS[name ?? ""] ?? ""
