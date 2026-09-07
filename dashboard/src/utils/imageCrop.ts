// Geometry for the crop frame. Kept out of the component because a bad number here is
// invisible until someone's face is half outside the circle, and a component cannot be
// unit tested in this project.

export interface Size {
	width: number
	height: number
}

export interface Point {
	x: number
	y: number
}

export function clamp(value: number, low: number, high: number): number {
	return Math.min(high, Math.max(low, value))
}

/** The image's footprint once rotated: a quarter turn swaps the axes. */
export function rotatedSize(size: Size, rotation: number): Size {
	const turned = ((rotation % 360) + 360) % 360
	if (turned % 180 === 0) return size
	return { width: size.height, height: size.width }
}

/**
 * The scale at which the image covers the frame with nothing left over — the larger of
 * the two ratios, which is what makes the other axis overflow instead of leaving a gap.
 */
export function coverScale(size: Size, frame: Size): number {
	if (!size.width || !size.height || !frame.width || !frame.height) return 1
	return Math.max(frame.width / size.width, frame.height / size.height)
}

/**
 * The pan, held inside the overflow. Dragging is free until an edge of the image would
 * come into the frame; past that the offset stops, so no dead space can appear. An image
 * that exactly fills the frame has no overflow and so cannot be panned at all.
 */
export function clampOffset(point: Point, rendered: Size, frame: Size): Point {
	const limitX = Math.max(0, (rendered.width - frame.width) / 2)
	const limitY = Math.max(0, (rendered.height - frame.height) / 2)
	return {
		x: clamp(point.x, -limitX, limitX),
		y: clamp(point.y, -limitY, limitY),
	}
}
