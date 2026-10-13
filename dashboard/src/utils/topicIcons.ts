import type { Component } from "vue"
import LucideBitcoin from "~icons/lucide/bitcoin"
import LucideBookOpen from "~icons/lucide/book-open"
import LucideCamera from "~icons/lucide/camera"
import LucideClapperboard from "~icons/lucide/clapperboard"
import LucideDumbbell from "~icons/lucide/dumbbell"
import LucideFlaskConical from "~icons/lucide/flask-conical"
import LucideGamepad2 from "~icons/lucide/gamepad-2"
import LucideGraduationCap from "~icons/lucide/graduation-cap"
import LucideHandHeart from "~icons/lucide/hand-heart"
import LucideHeartPulse from "~icons/lucide/heart-pulse"
import LucideLaptop from "~icons/lucide/laptop"
import LucideMusic from "~icons/lucide/music"
import LucidePalette from "~icons/lucide/palette"
import LucidePenTool from "~icons/lucide/pen-tool"
import LucidePlane from "~icons/lucide/plane"
import LucideRocket from "~icons/lucide/rocket"
import LucideTag from "~icons/lucide/tag"
import LucideUtensils from "~icons/lucide/utensils"

// Keyed by Event Topic name, as shipped in buzz/fixtures/event_topic.json. Topics an admin
// adds on a site fall back to a plain tag.
const TOPIC_ICONS: Record<string, Component> = {
	"Art & Culture": LucidePalette,
	Books: LucideBookOpen,
	Community: LucideHandHeart,
	Crypto: LucideBitcoin,
	Design: LucidePenTool,
	Education: LucideGraduationCap,
	Film: LucideClapperboard,
	"Food & Drinks": LucideUtensils,
	Gaming: LucideGamepad2,
	"Health & Wellness": LucideHeartPulse,
	Music: LucideMusic,
	Photography: LucideCamera,
	Science: LucideFlaskConical,
	"Sports & Fitness": LucideDumbbell,
	Startups: LucideRocket,
	Tech: LucideLaptop,
	Travel: LucidePlane,
}

export const topicIcon = (topic: string): Component => TOPIC_ICONS[topic] ?? LucideTag
