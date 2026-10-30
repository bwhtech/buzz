import { dayjsLocal } from "frappe-ui"
import { computed, toValue, type MaybeRefOrGetter } from "vue"

const clock = (time: string) => dayjsLocal(`2000-01-01 ${time}`).format("h:mm A")

export function useEventDateLabels(eventDetails: MaybeRefOrGetter<Record<string, any>>) {
	const event = computed(() => toValue(eventDetails))
	const startDate = computed(() => dayjsLocal(event.value.start_date))

	const dateLabel = computed(() => {
		const { start_date, end_date } = event.value
		if (!start_date) return ""
		const start = startDate.value.format("ddd, MMM D, YYYY")
		if (!end_date || end_date === start_date) return start
		return `${startDate.value.format("MMM D")} – ${dayjsLocal(end_date).format("MMM D, YYYY")}`
	})

	const timeLabel = computed(() => {
		const { start_time, end_time, time_zone_label } = event.value
		if (!start_time) return ""
		const range = end_time ? `${clock(start_time)} – ${clock(end_time)}` : clock(start_time)
		return time_zone_label ? `${range} ${time_zone_label}` : range
	})

	const venueLabel = computed(
		() => event.value.venue_name || (event.value.medium === "Online" ? __("Online") : ""),
	)

	return { startDate, dateLabel, timeLabel, venueLabel }
}
