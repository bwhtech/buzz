// Deterministic stand-in for a missing banner: contour rings whose origin, spacing and
// squash come from the event name, so an event always draws the same pattern.

const LINE = "var(--outline-gray-2)"
const LINE_WIDTH = 2
const SURFACE = "var(--surface-gray-1)"

/** FNV-1a seed, then xorshift — successive draws stay independent of each other. */
function randomFrom(seed: string): () => number {
	let state = 2166136261
	for (const character of seed) {
		state = Math.imul(state ^ character.charCodeAt(0), 16777619)
	}
	return () => {
		state ^= state << 13
		state ^= state >>> 17
		state ^= state << 5
		return (state >>> 0) / 4294967296
	}
}

const between = (draw: number, low: number, high: number) => low + draw * (high - low)

/** Origins skip the middle of the square: centred rings read as a target, not a contour map. */
const offCentre = (draw: number) =>
	draw < 0.5 ? between(draw * 2, -10, 30) : between(draw * 2 - 1, 70, 110)

export function bannerPattern(seed: string): string {
	const next = randomFrom(seed)
	const originX = Math.round(offCentre(next()))
	const originY = Math.round(offCentre(next()))
	// Squashing one axis is what keeps the rings from reading as a bullseye.
	const width = Math.round(between(next(), 55, 110))
	const height = Math.round(between(next(), 55, 110))
	const gap = between(next(), 18, 26).toFixed(1)

	return (
		`repeating-radial-gradient(ellipse ${width}% ${height}% at ${originX}% ${originY}%,` +
		` ${LINE} 0 ${LINE_WIDTH}px, transparent ${LINE_WIDTH}px ${gap}px),` +
		` linear-gradient(${SURFACE}, ${SURFACE})`
	)
}
