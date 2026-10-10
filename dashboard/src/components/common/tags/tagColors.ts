import type { TagColor } from "@/types"

// Hues far enough apart to tell a row of dots apart. Whole class strings, so Tailwind finds them.
export const TAG_COLOR_CLASSES: Record<TagColor, { chip: string; dot: string }> = {
	gray: { chip: "bg-surface-gray-2 text-ink-gray-7", dot: "bg-surface-gray-6" },
	red: { chip: "bg-surface-red-2 text-ink-red-7", dot: "bg-surface-red-6" },
	orange: { chip: "bg-surface-orange-2 text-ink-orange-7", dot: "bg-surface-orange-6" },
	yellow: { chip: "bg-surface-yellow-2 text-ink-yellow-7", dot: "bg-surface-yellow-6" },
	green: { chip: "bg-surface-green-2 text-ink-green-7", dot: "bg-surface-green-6" },
	cyan: { chip: "bg-surface-cyan-2 text-ink-cyan-7", dot: "bg-surface-cyan-6" },
	blue: { chip: "bg-surface-blue-2 text-ink-blue-7", dot: "bg-surface-blue-6" },
	purple: { chip: "bg-surface-purple-2 text-ink-purple-7", dot: "bg-surface-purple-6" },
	pink: { chip: "bg-surface-pink-2 text-ink-pink-7", dot: "bg-surface-pink-6" },
}

export const TAG_COLORS = Object.keys(TAG_COLOR_CLASSES) as TagColor[]

export const tagColorClasses = (color: TagColor) =>
	TAG_COLOR_CLASSES[color] ?? TAG_COLOR_CLASSES.gray
