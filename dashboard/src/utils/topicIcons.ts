import type { Component } from "vue"
import LucideBitcoin from "~icons/lucide/bitcoin"
import LucideDumbbell from "~icons/lucide/dumbbell"
import LucideGraduationCap from "~icons/lucide/graduation-cap"
import LucideHandHeart from "~icons/lucide/hand-heart"
import LucideHeartPulse from "~icons/lucide/heart-pulse"
import LucideLaptop from "~icons/lucide/laptop"
import LucideMusic from "~icons/lucide/music"
import LucidePalette from "~icons/lucide/palette"
import LucidePenTool from "~icons/lucide/pen-tool"
import LucideRocket from "~icons/lucide/rocket"
import LucideSparkles from "~icons/lucide/sparkles"
import LucideTag from "~icons/lucide/tag"
import LucideUtensils from "~icons/lucide/utensils"

// Keyed by Event Topic name, as shipped in buzz/fixtures/event_topic.json. Topics an admin
// adds on a site fall back to a plain tag.
const TOPIC_ICONS: Record<string, Component> = {
	AI: LucideSparkles,
	"Art & Culture": LucidePalette,
	Community: LucideHandHeart,
	Crypto: LucideBitcoin,
	Design: LucidePenTool,
	Education: LucideGraduationCap,
	"Food & Drinks": LucideUtensils,
	"Health & Wellness": LucideHeartPulse,
	Music: LucideMusic,
	"Sports & Fitness": LucideDumbbell,
	Startups: LucideRocket,
	Tech: LucideLaptop,
}

export const topicIcon = (topic: string): Component => TOPIC_ICONS[topic] ?? LucideTag
