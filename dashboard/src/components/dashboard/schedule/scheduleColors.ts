// Tailwind sees class names only when they are written out in full.
const THEMES: Record<string, string> = {
	gray: "border-outline-gray-2 bg-surface-gray-2 text-ink-gray-8",
	blue: "border-outline-blue-1 bg-surface-blue-1 text-ink-blue-7",
	green: "border-outline-green-1 bg-surface-green-1 text-ink-green-7",
	red: "border-outline-red-1 bg-surface-red-1 text-ink-red-7",
	orange: "border-outline-orange-1 bg-surface-orange-1 text-ink-orange-7",
	yellow: "border-outline-amber-1 bg-surface-amber-1 text-ink-amber-7",
	teal: "border-outline-green-1 bg-surface-green-1 text-ink-green-7",
	cyan: "border-outline-blue-1 bg-surface-blue-1 text-ink-cyan-7",
	purple: "border-outline-gray-2 bg-surface-gray-2 text-ink-purple-7",
	pink: "border-outline-red-1 bg-surface-red-1 text-ink-pink-7",
}

const DOTS: Record<string, string> = {
	gray: "bg-surface-gray-5",
	blue: "bg-surface-blue-6",
	green: "bg-surface-green-6",
	red: "bg-surface-red-6",
	orange: "bg-surface-amber-5",
	yellow: "bg-surface-amber-5",
	teal: "bg-surface-green-6",
	cyan: "bg-surface-blue-6",
	purple: "bg-surface-gray-7",
	pink: "bg-surface-red-6",
}

export const TRACK_COLORS = ["blue", "green", "purple", "orange", "teal", "pink"]

const isHex = (color: string | null | undefined): color is string =>
	/^#[0-9a-f]{6}$/i.test(color ?? "")

export function colorClasses(color: string | null | undefined): string {
	return isHex(color) ? "" : (THEMES[color ?? ""] ?? THEMES.gray)
}

export function dotClasses(color: string | null | undefined): string {
	return isHex(color) ? "" : (DOTS[color ?? ""] ?? DOTS.gray)
}

/** A hex color carries its own style; a theme name is covered by its classes. */
export function colorStyle(color: string | null | undefined) {
	if (!isHex(color)) return undefined
	return { color, borderColor: `${color}55`, backgroundColor: `${color}1f` }
}
