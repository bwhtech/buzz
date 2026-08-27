export function isImage(extension: string | null | undefined): boolean {
	if (!extension) return false
	return ["png", "jpg", "jpeg", "gif", "svg", "bmp", "webp"].includes(extension.toLowerCase())
}

export function validateIsImageFile(file: File): string | void {
	const extn = file.name.split(".").pop()?.toLowerCase()
	if (!isImage(extn)) {
		return "Only image files are allowed"
	}
}

/**
 * Clear all booking-related data from localStorage
 * This removes all keys that start with 'event-booking-'
 */
export function clearBookingCache(): void {
	const keysToRemove: string[] = []
	for (let i = 0; i < localStorage.length; i++) {
		const key = localStorage.key(i)
		if (key && key.startsWith("event-booking-")) {
			keysToRemove.push(key)
		}
	}
	keysToRemove.forEach((key) => localStorage.removeItem(key))
}
