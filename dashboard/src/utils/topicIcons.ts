import { type Component, h } from "vue"
import LucideGraduationCap from "~icons/lucide/graduation-cap"
import LucideHandHeart from "~icons/lucide/hand-heart"
import LucideLaptop from "~icons/lucide/laptop"
import LucidePalette from "~icons/lucide/palette"
import LucidePenTool from "~icons/lucide/pen-tool"
import LucideRocket from "~icons/lucide/rocket"
import LucideSparkles from "~icons/lucide/sparkles"
import LucideTag from "~icons/lucide/tag"

// Lucide has no open source mark; this is the brand-open-source path from Tabler Icons.
const OpenSourceIcon: Component = () =>
	h(
		"svg",
		{
			viewBox: "0 0 24 24",
			fill: "none",
			stroke: "currentColor",
			"stroke-width": 2,
			"stroke-linecap": "round",
			"stroke-linejoin": "round",
			width: 24,
			height: 24,
		},
		[
			h("path", {
				d: "M12 3a9 9 0 0 1 3.618 17.243l-2.193 -5.602a3 3 0 1 0 -2.849 0l-2.193 5.603a9 9 0 0 1 3.617 -17.244",
			}),
		],
	)

// Keyed by Event Topic name, as shipped in buzz/fixtures/event_topic.json. Topics an admin
// adds on a site fall back to a plain tag.
const TOPIC_ICONS: Record<string, Component> = {
	AI: LucideSparkles,
	"Art & Culture": LucidePalette,
	Community: LucideHandHeart,
	Design: LucidePenTool,
	Education: LucideGraduationCap,
	"Open Source": OpenSourceIcon,
	Startups: LucideRocket,
	Tech: LucideLaptop,
}

export const topicIcon = (topic: string): Component => TOPIC_ICONS[topic] ?? LucideTag
