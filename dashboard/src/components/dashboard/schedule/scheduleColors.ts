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

export const ROOM_COLORS = ["blue", "purple", "green", "yellow", "pink", "cyan", "orange"]

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
		return { background: `${color}1f`, border: `${color}55`, meta: color, title: color, dot: color }
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

type BadgeTheme = "gray" | "blue" | "green" | "red" | "amber" | "violet"
// frappe-ui Badge lacks these themes, so each borrows the nearest one.
const BADGE_REMAPS: Record<string, BadgeTheme> = {
	orange: "amber",
	teal: "green",
	cyan: "blue",
	pink: "red",
}

export function badgeTheme(color: string | null | undefined) {
	const theme = themeOf(color)
	return BADGE_REMAPS[theme] ?? (theme as BadgeTheme)
}
