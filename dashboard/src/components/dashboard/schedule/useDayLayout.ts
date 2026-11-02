import { computed } from "vue"

import { lanesOf } from "./scheduleLayout"
import { useBoard, useBuilder } from "./useScheduleBoard"

/** The active day's items arranged for a grid of tracks. */
export function useDayLayout() {
	const builder = useBuilder()
	const board = useBoard()
	const tracks = builder.tracks.tracks
	const dayItems = computed(() => builder.dayItems(builder.activeDate.value))
	const trackIndex = computed(() =>
		Object.fromEntries(tracks.value.map((track, index) => [track.name, index])),
	)
	const visible = computed(() =>
		dayItems.value.filter((item) => !item.track || trackIndex.value[item.track] !== undefined),
	)
	const conflicts = computed(() => builder.conflicts(dayItems.value))
	const lanes = computed(() =>
		Object.assign(
			{},
			...tracks.value.map((track) =>
				lanesOf(dayItems.value.filter((item) => item.track === track.name)),
			),
		),
	)
	const countIn = (track: string) => dayItems.value.filter((item) => item.track === track).length
	return { builder, board, tracks, dayItems, trackIndex, visible, conflicts, lanes, countIn }
}
