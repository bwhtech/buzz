// frappe-ui's Badge only themes these five colours.
export type BadgeTheme = "blue" | "red" | "green" | "gray" | "amber"

// Tailwind emits only the classes it can see, so the dot colours are written out per
// theme rather than interpolated. The `ink` scale is registered as a text colour, not a
// background one, so the token is reached through its variable.
const THEME_DOTS: Record<BadgeTheme, string> = {
	blue: "bg-[--ink-blue-5]",
	red: "bg-[--ink-red-5]",
	green: "bg-[--ink-green-5]",
	amber: "bg-[--ink-amber-5]",
	gray: "bg-[--ink-gray-5]",
}

export const badgeDotClass = (theme: BadgeTheme) => THEME_DOTS[theme]
