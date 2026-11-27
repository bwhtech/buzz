import { dayjsLocal } from "frappe-ui"
import { computed, ref } from "vue"

import {
	type ScheduleDraft,
	formatDateLabel,
	formatDuration,
	formatTime,
	minutesOf,
	scheduleLength,
	timeOf,
} from "./scheduleTime"

export type Phase = "start" | "end"

const isoDate = (day: ReturnType<typeof dayjsLocal>) => day.format("YYYY-MM-DD")

/** Today, tomorrow, the day after and the coming weekend; on a Sunday the weekend is today. */
export function quickDates() {
	const now = dayjsLocal()
	const saturday = now.day() === 0 ? now : now.add(6 - now.day(), "day")
	const sunday = now.day() === 0 ? now : saturday.add(1, "day")
	const single = (label: string, day: ReturnType<typeof dayjsLocal>) => ({
		label,
		hint: day.format("ddd D"),
		start: isoDate(day),
		end: isoDate(day),
	})
	return [
		single("Today", now),
		single("Tomorrow", now.add(1, "day")),
		single("Day after", now.add(2, "day")),
		{
			label: "Weekend",
			hint: `${saturday.format("ddd D")}–${sunday.format("D")}`,
			start: isoDate(saturday),
			end: isoDate(sunday),
		},
	]
}

/** Schedule edits that keep an event's length, and never let it end before it starts. */
export function useScheduleEdits(schedule: ScheduleDraft) {
	function moveStart(patch: { date?: string; time?: string }) {
		const length = scheduleLength(schedule)
		if (patch.date) schedule.startDate = patch.date
		if (patch.time) schedule.startTime = patch.time
		const end = dayjsLocal(`${schedule.startDate} ${schedule.startTime}`).add(
			length > 0 ? length : 60,
			"minute",
		)
		schedule.endDate = end.format("YYYY-MM-DD")
		schedule.endTime = end.format("HH:mm:00")
	}

	// A same-day end at or before the start moves to an hour after it, into the next day if it must.
	function ensureEndAfterStart() {
		if (schedule.endDate < schedule.startDate) schedule.endDate = schedule.startDate
		if (schedule.endDate !== schedule.startDate) return
		if (minutesOf(schedule.endTime) > minutesOf(schedule.startTime)) return
		const end = minutesOf(schedule.startTime) + 60
		if (end >= 24 * 60)
			schedule.endDate = dayjsLocal(schedule.startDate).add(1, "day").format("YYYY-MM-DD")
		schedule.endTime = timeOf(end % (24 * 60))
	}

	const startTime = computed({
		get: () => schedule.startTime,
		set: (time: string) => moveStart({ time }),
	})
	const endTime = computed({
		get: () => schedule.endTime,
		set: (time: string) => {
			schedule.endTime = time
			ensureEndAfterStart()
		},
	})

	return { moveStart, ensureEndAfterStart, startTime, endTime }
}

/**
 * Picking a range runs in two phases. The first tap sets the start, with the end on the
 * same day until told otherwise, and then asks for the end. Leaving while it still asks
 * keeps that same-day end.
 */
export function useScheduleRange(schedule: ScheduleDraft) {
	const edits = useScheduleEdits(schedule)
	const phase = ref<Phase>("start")
	const endChosen = ref(true)
	const hovered = ref("")

	const awaitingEnd = computed(() => phase.value === "end" && !endChosen.value)
	const sameDay = computed(() => schedule.endDate === schedule.startDate)
	// While asking for the end, the hovered day previews where the range would close.
	const shownEnd = computed(() =>
		awaitingEnd.value && hovered.value > schedule.startDate ? hovered.value : schedule.endDate,
	)

	function pickStart(date: string) {
		edits.moveStart({ date })
		schedule.endDate = date
		edits.ensureEndAfterStart()
		phase.value = "end"
		endChosen.value = false
	}

	function pickDate(date: string) {
		if (phase.value === "start" || date < schedule.startDate) return pickStart(date)
		schedule.endDate = date
		edits.ensureEndAfterStart()
		endChosen.value = true
	}

	function pickQuick(start: string, end: string) {
		edits.moveStart({ date: start })
		schedule.endDate = end
		edits.ensureEndAfterStart()
		phase.value = "end"
		endChosen.value = true
	}

	function keepSameDay() {
		schedule.endDate = schedule.startDate
		edits.ensureEndAfterStart()
		endChosen.value = true
	}

	function finish() {
		if (awaitingEnd.value) keepSameDay()
		phase.value = "start"
		hovered.value = ""
	}

	return {
		...edits,
		phase,
		hovered,
		awaitingEnd,
		sameDay,
		shownEnd,
		pickDate,
		pickQuick,
		keepSameDay,
		finish,
	}
}

export function scheduleLabels(schedule: ScheduleDraft) {
	const endDateLabel = computed(() =>
		schedule.endDate === schedule.startDate ? "Same day" : formatDateLabel(schedule.endDate),
	)
	// A multi-day event has no single length worth showing: it is not continuous.
	const lengthLabel = computed(() =>
		schedule.endDate === schedule.startDate ? formatDuration(scheduleLength(schedule)) : "",
	)
	const summaryLines = computed(() => {
		const start = `${formatDateLabel(schedule.startDate)} · ${formatTime(schedule.startTime)}`
		if (schedule.endDate === schedule.startDate)
			return [`${start} → ${formatTime(schedule.endTime)}`]
		const end = `${formatDateLabel(schedule.endDate)} · ${formatTime(schedule.endTime)}`
		return [`Starts ${start}`, `Ends ${end}`]
	})
	return { endDateLabel, lengthLabel, summaryLines }
}
