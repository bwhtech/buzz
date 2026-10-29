import { toast } from "frappe-ui"
import { type InjectionKey, computed, inject, provide, ref } from "vue"

import { nextFreeStart } from "../scheduleLayout"
import { useBuilder } from "../useScheduleBoard"

export type MobileView = "list" | "room" | "grid"
export type MobileSheet =
	| { type: "add"; start: number; room: string | null }
	| { type: "edit"; key: string }

export const ALL_ROOMS = "all"
const DEFAULT_DURATION = 30

export function useScheduleMobile() {
	const builder = useBuilder()
	const view = ref<MobileView>("list")
	const roomFilter = ref(ALL_ROOMS)
	const chosenRoom = ref<string | null>(null)
	const sheet = ref<MobileSheet | null>(null)

	const rooms = builder.rooms.rooms
	const roomView = computed(() => rooms.value.find((room) => room.name === chosenRoom.value))
	const activeRoom = computed(() => (roomView.value ?? rooms.value[0])?.name ?? null)
	const unscheduledTalks = computed(() =>
		builder.talks.value.filter(
			(talk) => !builder.items.value.some((item) => item.talk === talk.name),
		),
	)

	function defaultRoom() {
		if (view.value === "room") return activeRoom.value
		return roomFilter.value === ALL_ROOMS ? activeRoom.value : roomFilter.value
	}

	function openAdd(start?: number, room?: string | null) {
		const target = room === undefined ? defaultRoom() : room
		const date = builder.activeDate.value
		const at =
			start ??
			nextFreeStart(builder.dayItems(date), target, DEFAULT_DURATION, builder.rangeOf(date))
		sheet.value = { type: "add", start: at, room: target }
	}

	const openEdit = (key: string) => (sheet.value = { type: "edit", key })
	const closeSheet = () => (sheet.value = null)

	function addRoom() {
		const title = `Room ${rooms.value.length + 1}`
		return builder.rooms
			.add(title)
			.then(() => {
				chosenRoom.value = rooms.value.at(-1)?.name ?? null
				builder.say(`Added ${title}`)
			})
			.catch(() => toast.error("Could not add the room"))
	}

	return {
		view,
		roomFilter,
		chosenRoom,
		activeRoom,
		sheet,
		unscheduledTalks,
		openAdd,
		openEdit,
		closeSheet,
		addRoom,
	}
}

export type ScheduleMobile = ReturnType<typeof useScheduleMobile>
const mobileKey: InjectionKey<ScheduleMobile> = Symbol("scheduleMobile")

export const provideScheduleMobile = (mobile: ScheduleMobile) => provide(mobileKey, mobile)
export const useMobile = () => inject(mobileKey)!
