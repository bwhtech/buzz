import { toast } from "frappe-ui"
import { type InjectionKey, computed, inject, provide, ref } from "vue"

import { nextFreeStart } from "../scheduleLayout"
import { useBuilder } from "../useScheduleBoard"

export type MobileView = "list" | "track" | "grid"
export type MobileSheet =
	| { type: "add"; start: number; track: string | null }
	| { type: "edit"; key: string }

export const ALL_TRACKS = "all"
const DEFAULT_DURATION = 30

export function useScheduleMobile() {
	const builder = useBuilder()
	const view = ref<MobileView>("list")
	const trackFilter = ref(ALL_TRACKS)
	const chosenTrack = ref<string | null>(null)
	const sheet = ref<MobileSheet | null>(null)

	const tracks = builder.tracks.tracks
	const trackView = computed(() => tracks.value.find((track) => track.name === chosenTrack.value))
	const activeTrack = computed(() => (trackView.value ?? tracks.value[0])?.name ?? null)
	const unscheduledTalks = builder.unscheduledTalks

	function defaultTrack() {
		if (view.value === "track") return activeTrack.value
		return trackFilter.value === ALL_TRACKS ? activeTrack.value : trackFilter.value
	}

	function openAdd(start?: number, track?: string | null) {
		const target = track === undefined ? defaultTrack() : track
		const date = builder.activeDate.value
		const at =
			start ??
			nextFreeStart(builder.dayItems(date), target, DEFAULT_DURATION, builder.rangeOf(date))
		sheet.value = { type: "add", start: at, track: target }
	}

	const openEdit = (key: string) => (sheet.value = { type: "edit", key })
	const closeSheet = () => (sheet.value = null)

	function addTrack() {
		const title = `Track ${tracks.value.length + 1}`
		return builder.tracks
			.add(title)
			.then(() => {
				chosenTrack.value = tracks.value.at(-1)?.name ?? null
				builder.showToast(`Added ${title}`)
			})
			.catch(() => toast.error("Could not add the track"))
	}

	return {
		view,
		trackFilter,
		chosenTrack,
		activeTrack,
		sheet,
		unscheduledTalks,
		openAdd,
		openEdit,
		closeSheet,
		addTrack,
	}
}

export type ScheduleMobile = ReturnType<typeof useScheduleMobile>
const mobileKey: InjectionKey<ScheduleMobile> = Symbol("scheduleMobile")

export const provideScheduleMobile = (mobile: ScheduleMobile) => provide(mobileKey, mobile)
export const useMobile = () => inject(mobileKey)!
