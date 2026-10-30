import { useDebounceFn } from "@vueuse/core"
import { dayjs, toast, useCall, useDoc, useList } from "frappe-ui"
import { computed, ref, shallowRef, watch } from "vue"

import type { FrappeError } from "@/types"

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
import { useScheduleTracks } from "./useScheduleTracks"

interface Draft {
	days: ScheduleDay[]
	items: ScheduleItem[]
	published: 0 | 1
}

export type SaveState = "saved" | "saving" | "unsaved" | "error"

const deepCopy = <T>(value: T): T => JSON.parse(JSON.stringify(value))
const AUTOSAVE_MS = 800

export function useScheduleBuilder(eventId: () => string) {
	const scheduleName = ref("")
	const openCall = useCall<string, { event: string }>({
		url: "/api/v2/method/buzz.api.schedule.get_or_create_schedule",
		method: "POST",
		immediate: false,
	})
	const open = () =>
		openCall.submit({ event: eventId() }).then((name) => (scheduleName.value = String(name)))

	const schedule = useDoc<ScheduleDoc>({ doctype: "Buzz Schedule", name: () => scheduleName.value })
	const copyTrackCall = useCall<string, { schedule: string; track: string }>({
		url: "/api/v2/method/buzz.api.schedule.fork_standard_track",
		method: "POST",
		immediate: false,
	})
	const tracks = useScheduleTracks(
		() => scheduleName.value,
		(track) => items.value.some((item) => item.track === track),
	)
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
	const talkDuration = computed(() => typesByName.value.Talk?.default_duration ?? 30)

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
	const findItem = (key: string) => items.value.find((entry) => entry.key === key)
	const nextDayDate = () => dayjs(days.value.at(-1)?.date).add(1, "day").format("YYYY-MM-DD")
	const dayOptions = computed(() =>
		days.value.map((day) => ({ label: day.label, value: day.date })),
	)
	const trackOptions = computed(() => [
		{ label: "All tracks", value: "all" },
		...tracks.tracks.value.map((track) => ({ label: track.title, value: track.name })),
	])
	const unscheduledTalks = computed(() => {
		const scheduled = new Set(items.value.map((item) => item.talk))
		return talks.value.filter((talk) => !scheduled.has(talk.name))
	})

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

	async function saveWithToast(publish?: boolean) {
		try {
			await save(publish)
			if (publish !== undefined)
				toast.success(publish ? "Schedule published" : "Schedule unpublished")
		} catch (error) {
			toast.error((error as FrappeError).message || "Could not save the schedule")
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

	const toastMessage = ref<string | null>(null)
	let toastTimer: ReturnType<typeof setTimeout> | undefined
	const undoPoint = shallowRef<{ items: ScheduleItem[]; days: ScheduleDay[] } | null>(null)
	const canUndo = computed(() => !!undoPoint.value)
	function showToast(message?: string | null) {
		if (!message) return
		clearTimeout(toastTimer)
		toastMessage.value = message
		toastTimer = setTimeout(() => (toastMessage.value = null), 3500)
	}
	function saveUndoPoint() {
		if (draft.value)
			undoPoint.value = deepCopy({ items: draft.value.items, days: draft.value.days })
	}
	function applyChange(change: (current: Draft) => void, message?: string) {
		if (!draft.value) return
		saveUndoPoint()
		change(draft.value)
		showToast(message)
	}
	function undo() {
		if (!draft.value || !undoPoint.value) return
		Object.assign(draft.value, undoPoint.value)
		undoPoint.value = null
		toastMessage.value = null
	}

	const conflicts = (list: ScheduleItem[]) =>
		conflictsOf(list, { talks: talksByName.value, trackTitle: tracks.titleOf })
	const conflictCount = computed(() =>
		days.value
			.map((day) => Object.keys(conflicts(dayItems(day.date))).length)
			.reduce((a, b) => a + b, 0),
	)
	const conflictOf = (item: ScheduleItem) => conflicts(dayItems(item.date))[item.key]
	const rangeOf = (date: string) => dayRange(dayItems(date))
	const dayLabel = (date: string) => days.value.find((day) => day.date === date)?.label ?? date

	function itemDetails(item: ScheduleItem) {
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
		applyChange((current) => current.items.push(item), message)
		return item
	}

	function place(
		payload: Pick<DragPayload, "kind" | "id">,
		date: string,
		track?: string | null,
		start?: number,
	) {
		if (payload.kind === "item") return moveItem(payload.id, date, track, start)
		const defaultTrack = tracks.tracks.value[0]?.name ?? null
		if (payload.kind === "talk")
			return placeTalk(payload.id, date, track === undefined ? defaultTrack : track, start)
		return placeType(payload.id, date, track, start)
	}

	function moveItem(key: string, date: string, track?: string | null, start?: number) {
		const item = findItem(key)
		if (!item) return
		const patch: Partial<ScheduleItem> = { date, start: start ?? item.start }
		if (track !== undefined && item.track) patch.track = track
		const moved =
			date !== item.date
				? `Moved to ${dayLabel(date)}`
				: patch.track && patch.track !== item.track
					? `Moved to ${tracks.titleOf(patch.track)}`
					: undefined
		update(key, patch, moved)
	}

	function placeTalk(name: string, date: string, track: string | null, start?: number) {
		const talk = talksByName.value[name]
		if (!talk) return
		const duration = talkDuration.value
		const existing = items.value.find((entry) => entry.talk === name)
		const at = start ?? nextFreeStart(dayItems(date), track, duration, rangeOf(date))
		if (existing) return update(existing.key, { date, track, start: at }, `Moved “${talk.title}”`)
		add(
			{ date, track, start: at, duration, type: "Talk", title: talk.title, talk: name },
			`Scheduled for ${dayLabel(date)}, ${clock(at)}`,
		)
	}

	function placeType(name: string, date: string, track?: string | null, start?: number) {
		const type = typesByName.value[name]
		if (!type) return
		const target = type.spans_all_tracks
			? null
			: track === undefined
				? (tracks.tracks.value[0]?.name ?? null)
				: track
		const at = start ?? nextFreeStart(dayItems(date), target, type.default_duration, rangeOf(date))
		const title = name === "Custom" ? "Untitled item" : type.title
		return add(
			{
				date,
				track: target,
				start: at,
				duration: type.default_duration,
				type: name,
				title,
				talk: null,
			},
			`Added ${title.toLowerCase()} at ${clock(at)}`,
		)
	}

	function addCustom(date: string, title: string, duration: number, track: string | null) {
		const type = typesByName.value.Custom
		const at = nextFreeStart(dayItems(date), track, duration, rangeOf(date))
		const name = title.trim() || "Untitled item"
		return add(
			{ date, track, start: at, duration, type: type?.name ?? "Custom", title: name, talk: null },
			`Added “${name}” at ${clock(at)}`,
		)
	}

	function update(key: string, patch: Partial<ScheduleItem>, message?: string) {
		applyChange((current) => {
			const item = current.items.find((entry) => entry.key === key)
			if (item) Object.assign(item, patch)
		}, message)
	}

	function retitle(key: string, title: string) {
		const item = findItem(key)
		if (item) item.title = title
	}

	function resize(key: string, duration: number) {
		const item = findItem(key)
		if (item) item.duration = Math.max(MIN_DURATION, duration)
	}

	function remove(key: string) {
		const item = findItem(key)
		if (!item) return
		const title = itemDetails(item).title
		applyChange(
			(current) => (current.items = current.items.filter((entry) => entry.key !== key)),
			item.talk ? `Unscheduled “${title}”` : `Removed “${title}”`,
		)
	}

	function duplicate(key: string) {
		const item = findItem(key)
		if (!item) return
		const start = nextFreeStart(dayItems(item.date), item.track, item.duration, rangeOf(item.date))
		const base = { ...item, start, talk: null, type: item.talk ? "Custom" : item.type }
		const title = item.talk ? `${itemDetails(item).title} (Q&A)` : item.title
		return add({ ...base, title }, `Duplicated at ${clock(start)}`)
	}

	function addDay() {
		const date = nextDayDate()
		applyChange(
			(current) => current.days.push({ date, label: `Day ${current.days.length + 1}` }),
			`Added Day ${days.value.length + 1}`,
		)
		activeDate.value = date
	}

	function editDay(date: string, next: ScheduleDay) {
		applyChange((current) => {
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
		const target = nextDayDate()
		applyChange((current) => {
			current.days.push({ date: target, label: `${source.label} copy` })
			for (const item of dayItems(date))
				current.items.push({ ...deepCopy(item), key: newKey(), date: target })
		}, `Duplicated ${source.label}`)
		activeDate.value = target
	}

	function removeDay(date: string) {
		applyChange(
			(current) => {
				current.days = current.days.filter((day) => day.date !== date)
				current.items = current.items.filter((item) => item.date !== date)
			},
			`Deleted ${dayLabel(date)}`,
		)
	}

	// The standard track is shared, so an edit gives this schedule a copy and moves its items there.
	async function editableTrack(name: string) {
		if (!tracks.find(name)?.is_standard) return name
		const copiedTrack = String(
			await copyTrackCall.submit({ schedule: scheduleName.value, track: name }),
		)
		await tracks.reload()
		for (const item of items.value) if (item.track === name) item.track = copiedTrack
		savedSnapshot.value = savedSnapshot.value.replaceAll(
			`"track":"${name}"`,
			`"track":"${copiedTrack}"`,
		)
		return copiedTrack
	}

	async function renameTrack(name: string, title: string) {
		await tracks.rename(await editableTrack(name), title)
		await tracks.reload()
	}

	async function moveTrack(name: string, step: -1 | 1) {
		const order = tracks.tracks.value.map((track) => track.name)
		const neighbor = order[order.indexOf(name) + step]
		const moved = await editableTrack(name)
		if (neighbor) await editableTrack(neighbor)
		await tracks.move(moved, step)
	}

	// Deleting saves at once, so on a live schedule it would publish every other pending edit.
	async function removeTrack(name: string) {
		if (!draft.value) return
		if (isPublished.value && dirty.value)
			throw new Error("Publish or undo your changes before deleting a track")
		const track = tracks.find(name)
		draft.value.items = draft.value.items.filter((item) => item.track !== name)
		// Undo would bring back items that point at the deleted track.
		undoPoint.value = null
		await save()
		if (!track?.is_standard) await tracks.remove(name)
		showToast(`Deleted ${track?.title}`)
	}

	return {
		open,
		openCall,
		schedule,
		draft,
		dirty,
		saveState,
		isPublished,
		save,
		saveWithToast,
		days,
		items,
		activeDate,
		activeDay,
		dayItems,
		findItem,
		dayOptions,
		trackOptions,
		conflictOf,
		dayLabel,
		rangeOf,
		types,
		typesByName,
		talks,
		unscheduledTalks,
		talkDuration,
		tracks,
		renameTrack,
		moveTrack,
		removeTrack,
		conflicts,
		conflictCount,
		itemDetails,
		toastMessage,
		undo,
		canUndo,
		showToast,
		saveUndoPoint,
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
