// The server names two colors differently from the design tokens.
const TOKEN_NAMES: Record<string, string> = { purple: "violet", yellow: "amber" }
const THEMES = new Set([
	"gray",
	"blue",
	"green",
	"red",
	"orange",
	"amber",
	"violet",
	"teal",
	"cyan",
	"pink",
])
const isHex = (color: string | null | undefined): color is string =>
	/^#[0-9a-f]{6}$/i.test(color ?? "")

export const TRACK_COLORS = ["blue", "purple", "green", "yellow", "pink", "cyan", "orange"]

function themeOf(color: string | null | undefined) {
	const name = TOKEN_NAMES[color ?? ""] ?? color ?? ""
	return THEMES.has(name) ? name : "gray"
}

export interface BlockColors {
	background: string
	border: string
	meta: string
	title: string
	dot: string
}

/** Tinted block colors for a theme name or a #rrggbb value. */
export function blockColors(color: string | null | undefined): BlockColors {
	if (isHex(color)) {
		// Mixing with the strongest ink keeps text readable in both light and dark mode.
		const ink = (percent: number) => `color-mix(in srgb, ${color} ${percent}%, var(--ink-gray-9))`
		return {
			background: `color-mix(in srgb, ${color} 12%, var(--surface-base))`,
			border: `color-mix(in srgb, ${color} 35%, var(--surface-base))`,
			meta: ink(75),
			title: ink(55),
			dot: color,
		}
	}
	const theme = themeOf(color)
	const gray = theme === "gray"
	return {
		background: `var(--surface-${theme}-${gray ? 2 : 1})`,
		border: `var(--outline-${theme}-2)`,
		meta: `var(--ink-${theme}-${gray ? 6 : 7})`,
		title: `var(--ink-${theme}-${gray ? 8 : 9})`,
		dot: `var(--surface-${theme}-${gray ? 5 : 6})`,
	}
}

export const dotColor = (color: string | null | undefined) => blockColors(color).dot

/** Inline colors that tint a frappe-ui Badge with an item type's color. */
export function badgeStyle(color: string | null | undefined) {
	const colors = blockColors(color)
	return { background: colors.background, color: colors.title }
}
