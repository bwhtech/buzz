// Keep in sync with ZOOM_BACKED_CATEGORIES in buzz/utils.py
const ZOOM_BACKED_CATEGORIES = ["Webinars", "Zoom Meeting"]

/** Zoom-backed events register attendees on Zoom, so they need a last name. */
export function isZoomBackedCategory(category: string | undefined | null): boolean {
	return !!category && ZOOM_BACKED_CATEGORIES.includes(category)
}
