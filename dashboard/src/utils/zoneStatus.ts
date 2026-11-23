import type { ZoneStatus } from "@/types"
import { checkInTimeLabel } from "@/utils/dateLabels"

export const zoneStatusLabel = (zone: ZoneStatus) => {
	if (zone.checked_in_at) return checkInTimeLabel(zone.checked_in_at)
	return zone.allowed ? "Not checked in" : "Not allowed"
}

export const zoneDotClass = (zone: ZoneStatus) => {
	if (zone.checked_in_at) return "bg-surface-green-6"
	return zone.allowed ? "bg-surface-gray-4" : "border border-outline-gray-4"
}
