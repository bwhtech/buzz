import { useDebounceFn } from "@vueuse/core"
import { dayjs, useCall, useDoc, useList } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { MIN_DURATION, clock, conflictsOf, dayRange, nextFreeStart } from "./scheduleLayout"
import { fromRow, newKey, toRow } from "./scheduleRows"
import type {
	DragPayload,
	ScheduleDay,
	ScheduleDoc,
	ScheduleItem,
	ScheduleItemType,
	ScheduleTalk,
} from "./scheduleTypes"
import { useScheduleRooms } from "./useScheduleRooms"

interface Draft {
	days: ScheduleDay[]
	items: ScheduleItem[]
	published: 0 | 1
}

export type SaveState = "saved" | "saving" | "unsaved" | "error"

const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value))
const AUTOSAVE_MS = 800

export function useScheduleBuilder(eventId: () => string) {
	const scheduleName = ref("")
	const opener = useCall<string, { event: string }>({
		url: "/api/v2/method/buzz.api.schedule.get_or_create_schedule",
		method: "POST",
		immediate: false,
	})
	const open = () =>
		opener.submit({ event: eventId() }).then((name) => (scheduleName.value = String(name)))

	const schedule = useDoc<ScheduleDoc>({ doctype: "Buzz Schedule", name: () => scheduleName.value })
	const rooms = useScheduleRooms(() => scheduleName.value)
	const typesList = useList<ScheduleItemType>({
		doctype: "Buzz Schedule Item Type",
		fields: [
			"name",
			"title",
			"color",
			"icon",
			"default_duration",
			"spans_all_tracks",
			"is_standard",
		],
		orderBy: "is_standard desc, creation asc" as "creation asc",
		limit: 100,
	})
	const talksCall = useCall<ScheduleTalk[], { event: string }>({
		url: "/api/v2/method/buzz.api.schedule.get_schedule_talks",
		params: () => ({ event: eventId() }),
		refetch: true,
	})

	const types = computed(() => typesList.data ?? [])
	const typesByName = computed(() =>
		Object.fromEntries(types.value.map((type) => [type.name, type])),
	)
	const talks = computed(() => talksCall.data ?? [])
	const talksByName = computed(() =>
		Object.fromEntries(talks.value.map((talk) => [talk.name, talk])),
	)

	const draft = ref<Draft | null>(null)
	const days = computed(() => draft.value?.days ?? [])
	const items = computed(() => draft.value?.items ?? [])
	const isPublished = computed(() => !!draft.value?.published)
	const activeDate = ref("")
	watch(days, (list) => {
		if (!list.some((day) => day.date === activeDate.value)) activeDate.value = list[0]?.date ?? ""
	})
	const activeDay = computed(() => days.value.find((day) => day.date === activeDate.value))
	const dayItems = (date: string) => items.value.filter((item) => item.date === date)

	const serialized = () =>
		JSON.stringify({
			days: draft.value?.days,
			published: draft.value?.published,
			items: items.value.map(toRow),
		})
	const savedSnapshot = ref("")
	const dirty = computed(() => !!draft.value && serialized() !== savedSnapshot.value)
	const saveState = ref<SaveState>("saved")

	schedule.onSuccess((doc) => {
		if (draft.value) return
		const loaded = typeof doc.days === "string" ? JSON.parse(doc.days || "[]") : (doc.days ?? [])
		draft.value = { days: loaded, published: doc.is_published, items: doc.items.map(fromRow) }
		savedSnapshot.value = serialized()
	})

	async function save(publish?: boolean) {
		if (!draft.value) return
		if (publish !== undefined) draft.value.published = publish ? 1 : 0
		const sent = serialized()
		saveState.value = "saving"
		try {
			await schedule.setValue.submit({
				days: JSON.stringify(draft.value.days),
				is_published: draft.value.published,
				items: items.value.map(toRow) as unknown as ScheduleDoc["items"],
			})
			savedSnapshot.value = sent
			saveState.value = serialized() === sent ? "saved" : "unsaved"
		} catch (error) {
			saveState.value = "error"
			throw error
		}
	}

	// A live schedule changes only when published; a draft saves as it is edited.
	const autosave = useDebounceFn(
		() => !isPublished.value && dirty.value && save().catch(() => null),
		AUTOSAVE_MS,
	)
	watch(serialized, () => {
		if (!dirty.value) return
		if (saveState.value !== "saving") saveState.value = "unsaved"
		autosave()
	})

	const toast = ref<string | null>(null)
	let toastTimer: ReturnType<typeof setTimeout> | undefined
	let previous: { items: ScheduleItem[]; days: ScheduleDay[] } | null = null
	function say(message?: string | null) {
		if (!message) return
		clearTimeout(toastTimer)
		toast.value = message
		toastTimer = setTimeout(() => (toast.value = null), 3500)
	}
	function remember() {
		if (draft.value) previous = copy({ items: draft.value.items, days: draft.value.days })
	}
	function commit(change: (current: Draft) => void, message?: string) {
		if (!draft.value) return
		remember()
		change(draft.value)
		say(message)
	}
	function undo() {
		if (!draft.value || !previous) return
		Object.assign(draft.value, previous)
		previous = null
		toast.value = null
	}

	const conflicts = (list: ScheduleItem[]) =>
		conflictsOf(list, { talks: talksByName.value, roomTitle: rooms.titleOf })
	const conflictCount = computed(() =>
		days.value
			.map((day) => Object.keys(conflicts(dayItems(day.date))).length)
			.reduce((a, b) => a + b, 0),
	)
	const rangeOf = (date: string) => dayRange(dayItems(date))
	const dayLabel = (date: string) => days.value.find((day) => day.date === date)?.label ?? date

	function resolve(item: ScheduleItem) {
		const talk = item.talk ? talksByName.value[item.talk] : null
		const type = typesByName.value[item.type]
		return {
			title: talk?.title || item.title || "Untitled item",
			speakers: talk?.speakers ?? [],
			type,
		}
	}

	function add(change: Omit<ScheduleItem, "key">, message?: string) {
		const item = { ...change, key: newKey() }
		commit((current) => current.items.push(item), message)
		return item
	}

	function place(
		payload: Pick<DragPayload, "kind" | "id">,
		date: string,
		room?: string | null,
		start?: number,
	) {
		if (payload.kind === "item") return moveItem(payload.id, date, room, start)
		const defaultRoom = rooms.rooms.value[0]?.name ?? null
		if (payload.kind === "talk")
			return placeTalk(payload.id, date, room === undefined ? defaultRoom : room, start)
		return placeType(payload.id, date, room, start)
	}

	function moveItem(key: string, date: string, room?: string | null, start?: number) {
		const item = items.value.find((entry) => entry.key === key)
		if (!item) return
		const patch: Partial<ScheduleItem> = { date, start: start ?? item.start }
		if (room !== undefined && item.room) patch.room = room
		const moved =
			date !== item.date
				? `Moved to ${dayLabel(date)}`
				: patch.room && patch.room !== item.room
					? `Moved to ${rooms.titleOf(patch.room)}`
					: undefined
		update(key, patch, moved)
	}

	function placeTalk(name: string, date: string, room: string | null, start?: number) {
		const talk = talksByName.value[name]
		if (!talk) return
		const duration = typesByName.value.Talk?.default_duration ?? 30
		const existing = items.value.find((entry) => entry.talk === name)
		const at = start ?? nextFreeStart(dayItems(date), room, duration, rangeOf(date))
		if (existing) return update(existing.key, { date, room, start: at }, `Moved “${talk.title}”`)
		add(
			{ date, room, start: at, duration, type: "Talk", title: talk.title, talk: name },
			`Scheduled for ${dayLabel(date)}, ${clock(at)}`,
		)
	}

	function placeType(name: string, date: string, room?: string | null, start?: number) {
		const type = typesByName.value[name]
		if (!type) return
		const target = type.spans_all_tracks
			? null
			: room === undefined
				? (rooms.rooms.value[0]?.name ?? null)
				: room
		const at = start ?? nextFreeStart(dayItems(date), target, type.default_duration, rangeOf(date))
		const title = name === "Custom" ? "Untitled item" : type.title
		return add(
			{
				date,
				room: target,
				start: at,
				duration: type.default_duration,
				type: name,
				title,
				talk: null,
			},
			`Added ${title.toLowerCase()} at ${clock(at)}`,
		)
	}

	function addCustom(date: string, title: string, duration: number, room: string | null) {
		const type = typesByName.value.Custom
		const at = nextFreeStart(dayItems(date), room, duration, rangeOf(date))
		const name = title.trim() || "Untitled item"
		return add(
			{ date, room, start: at, duration, type: type?.name ?? "Custom", title: name, talk: null },
			`Added “${name}” at ${clock(at)}`,
		)
	}

	function update(key: string, patch: Partial<ScheduleItem>, message?: string) {
		commit((current) => {
			const item = current.items.find((entry) => entry.key === key)
			if (item) Object.assign(item, patch)
		}, message)
	}

	function retitle(key: string, title: string) {
		const item = items.value.find((entry) => entry.key === key)
		if (item) item.title = title
	}

	function resize(key: string, duration: number) {
		const item = items.value.find((entry) => entry.key === key)
		if (item) item.duration = Math.max(MIN_DURATION, duration)
	}

	function remove(key: string) {
		const item = items.value.find((entry) => entry.key === key)
		if (!item) return
		const title = resolve(item).title
		commit(
			(current) => (current.items = current.items.filter((entry) => entry.key !== key)),
			item.talk ? `Unscheduled “${title}”` : `Removed “${title}”`,
		)
	}

	function duplicate(key: string) {
		const item = items.value.find((entry) => entry.key === key)
		if (!item) return
		const start = nextFreeStart(dayItems(item.date), item.room, item.duration, rangeOf(item.date))
		const base = { ...item, start, talk: null, type: item.talk ? "Custom" : item.type }
		const title = item.talk ? `${resolve(item).title} (Q&A)` : item.title
		return add({ ...base, title }, `Duplicated at ${clock(start)}`)
	}

	function addDay() {
		const last = days.value.at(-1)
		const date = dayjs(last?.date).add(1, "day").format("YYYY-MM-DD")
		commit(
			(current) => current.days.push({ date, label: `Day ${current.days.length + 1}` }),
			`Added Day ${days.value.length + 1}`,
		)
		activeDate.value = date
	}

	function editDay(date: string, next: ScheduleDay) {
		commit((current) => {
			for (const item of current.items) if (item.date === date) item.date = next.date
			const day = current.days.find((entry) => entry.date === date)
			if (day) Object.assign(day, next)
			current.days.sort((a, b) => a.date.localeCompare(b.date))
		})
		activeDate.value = next.date
	}

	function duplicateDay(date: string) {
		const source = days.value.find((day) => day.date === date)
		if (!source) return
		const target = dayjs(days.value.at(-1)?.date).add(1, "day").format("YYYY-MM-DD")
		commit((current) => {
			current.days.push({ date: target, label: `${source.label} copy` })
			for (const item of dayItems(date))
				current.items.push({ ...copy(item), key: newKey(), date: target })
		}, `Duplicated ${source.label}`)
		activeDate.value = target
	}

	function removeDay(date: string) {
		commit(
			(current) => {
				current.days = current.days.filter((day) => day.date !== date)
				current.items = current.items.filter((item) => item.date !== date)
			},
			`Deleted ${dayLabel(date)}`,
		)
	}

	async function removeRoom(name: string) {
		const title = rooms.titleOf(name)
		commit((current) => (current.items = current.items.filter((item) => item.room !== name)))
		await save()
		await rooms.remove(name)
		say(`Deleted ${title}`)
	}

	return {
		open,
		opener,
		schedule,
		draft,
		dirty,
		saveState,
		isPublished,
		save,
		days,
		items,
		activeDate,
		activeDay,
		dayItems,
		dayLabel,
		rangeOf,
		types,
		typesByName,
		talks,
		rooms,
		removeRoom,
		conflicts,
		conflictCount,
		resolve,
		toast,
		undo,
		say,
		remember,
		place,
		addCustom,
		update,
		retitle,
		resize,
		remove,
		duplicate,
		addDay,
		editDay,
		duplicateDay,
		removeDay,
	}
}

export type ScheduleBuilder = ReturnType<typeof useScheduleBuilder>
