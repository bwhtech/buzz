import { dayjs, useCall, useDoc, useList } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { TRACK_COLORS } from "./scheduleColors"
import {
	DEFAULT_DURATION_MINUTES,
	conflictingKeys,
	endMinutes,
	nextFreeStart,
	startMinutes,
	toTime,
} from "./scheduleTime"
import type {
	ScheduleDay,
	ScheduleDoc,
	ScheduleItem,
	ScheduleItemType,
	ScheduleTalk,
	ScheduleTrack,
} from "./scheduleTypes"

interface Draft {
	days: ScheduleDay[]
	items: ScheduleItem[]
	is_published: 0 | 1
}

const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value))
const newKey = () => Math.random().toString(36).slice(2, 10)
const ITEM_FIELDS = [
	"name",
	"date",
	"type",
	"title",
	"reference_doctype",
	"reference_document",
	"all_tracks",
	"track",
	"start_time",
	"duration",
	"end_time",
] as const

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
	const tracksList = useList<ScheduleTrack>({
		doctype: "Buzz Schedule Track",
		fields: ["name", "title", "color"],
		filters: () => ({ schedule: scheduleName.value }),
		orderBy: "creation asc",
		limit: 50,
		immediate: false,
	})
	const typesList = useList<ScheduleItemType>({
		doctype: "Buzz Schedule Item Type",
		fields: ["name", "title", "color", "icon", "is_standard"],
		orderBy: "is_standard desc, title asc",
		limit: 100,
	})
	const talksCall = useCall<ScheduleTalk[], { event: string }>({
		url: "/api/v2/method/buzz.api.schedule.get_schedule_talks",
		params: () => ({ event: eventId() }),
		refetch: true,
	})

	const draft = ref<Draft | null>(null)
	const savedSnapshot = ref("")
	const dirty = computed(() => !!draft.value && JSON.stringify(draft.value) !== savedSnapshot.value)

	function reset(doc: ScheduleDoc) {
		const days = typeof doc.days === "string" ? JSON.parse(doc.days || "[]") : (doc.days ?? [])
		draft.value = {
			days,
			is_published: doc.is_published,
			items: copy(doc.items ?? []).map((item) => ({ ...item, key: newKey() })),
		}
		savedSnapshot.value = JSON.stringify(draft.value)
	}
	schedule.onSuccess((doc) => !dirty.value && reset(doc))

	const days = computed(() => draft.value?.days ?? [])
	const items = computed(() => draft.value?.items ?? [])
	const tracks = computed(() => tracksList.data ?? [])
	const itemTypes = computed(() => typesList.data ?? [])
	const talks = computed(() => {
		const placed = new Set(items.value.map((item) => item.reference_document))
		return (talksCall.data ?? []).filter((talk) => !placed.has(talk.name))
	})
	const conflicts = computed(() => conflictingKeys(items.value))
	const isPublished = computed(() => !!draft.value?.is_published)

	const activeDate = ref("")
	watch(days, (list) => {
		if (!list.some((day) => day.date === activeDate.value)) activeDate.value = list[0]?.date ?? ""
	})
	const activeDay = computed(() => days.value.find((day) => day.date === activeDate.value))
	const dayItems = (date: string) => items.value.filter((item) => item.date === date)

	async function save(publish?: boolean) {
		if (!draft.value) return
		if (publish !== undefined) draft.value.is_published = publish ? 1 : 0
		const sent = JSON.stringify(draft.value)
		const rows = draft.value.items.map((item) =>
			Object.fromEntries(ITEM_FIELDS.filter((field) => field in item).map((f) => [f, item[f]])),
		)
		const saved = (await schedule.setValue.submit({
			days: JSON.stringify(draft.value.days),
			is_published: draft.value.is_published,
			items: rows as unknown as ScheduleItem[],
		})) as ScheduleDoc
		if (JSON.stringify(draft.value) === sent) reset(saved)
		else savedSnapshot.value = sent
		talksCall.reload()
	}

	function addItem(patch: Partial<ScheduleItem> & Pick<ScheduleItem, "type">) {
		const date = patch.date ?? activeDate.value
		const track = patch.all_tracks ? null : (patch.track ?? tracks.value[0]?.name ?? null)
		const duration = patch.duration ?? DEFAULT_DURATION_MINUTES * 60
		const from = patch.start_time ? startMinutesOf(patch.start_time) : 9 * 60
		const start = patch.start_time
			? from
			: nextFreeStart(dayItems(date), track, from, duration / 60)
		const item: ScheduleItem = {
			title: "",
			all_tracks: 0,
			...patch,
			key: newKey(),
			date,
			track,
			duration,
			start_time: toTime(start),
		}
		item.end_time = toTime(endMinutes(item))
		draft.value?.items.push(item)
		return item
	}

	function updateItem(key: string, patch: Partial<ScheduleItem>) {
		const item = items.value.find((entry) => entry.key === key)
		if (!item) return
		Object.assign(item, patch)
		if (item.all_tracks) item.track = null
		item.end_time = toTime(endMinutes(item))
	}

	function removeItem(key: string) {
		if (draft.value) draft.value.items = draft.value.items.filter((item) => item.key !== key)
	}

	function addDay() {
		const last = days.value.at(-1)
		const date = last
			? dayjs(last.date).add(1, "day").format("YYYY-MM-DD")
			: dayjs().format("YYYY-MM-DD")
		draft.value?.days.push({ date, label: `Day ${days.value.length + 1}` })
		activeDate.value = date
	}

	function editDay(date: string, patch: ScheduleDay) {
		const day = days.value.find((entry) => entry.date === date)
		if (!day || !draft.value) return
		for (const item of items.value) if (item.date === date) item.date = patch.date
		Object.assign(day, patch)
		draft.value.days.sort((a, b) => a.date.localeCompare(b.date))
		activeDate.value = patch.date
	}

	function duplicateDay(date: string) {
		const source = days.value.find((day) => day.date === date)
		if (!source || !draft.value) return
		addDay()
		const target = days.value.find((day) => day.date === activeDate.value)!
		target.label = `${source.label} copy`
		for (const item of dayItems(date)) {
			draft.value.items.push({ ...copy(item), key: newKey(), name: undefined, date: target.date })
		}
	}

	function removeDay(date: string) {
		if (!draft.value) return
		draft.value.days = draft.value.days.filter((day) => day.date !== date)
		draft.value.items = draft.value.items.filter((item) => item.date !== date)
	}

	async function addTrack(title: string) {
		const color = TRACK_COLORS[tracks.value.length % TRACK_COLORS.length]
		await tracksList.insert.submit({
			title,
			color,
			schedule: scheduleName.value,
		} as Partial<ScheduleTrack>)
		await tracksList.reload()
	}

	async function renameTrack(name: string, title: string) {
		await tracksList.setValue.submit({ name, title })
	}

	async function removeTrack(name: string) {
		if (draft.value) draft.value.items = draft.value.items.filter((item) => item.track !== name)
		if (dirty.value) await save()
		await tracksList.delete.submit({ name })
		await tracksList.reload()
	}

	return {
		open,
		opener,
		scheduleName,
		schedule,
		draft,
		dirty,
		days,
		items,
		tracks,
		itemTypes,
		talks,
		conflicts,
		isPublished,
		activeDate,
		activeDay,
		dayItems,
		save,
		addItem,
		updateItem,
		removeItem,
		addDay,
		editDay,
		duplicateDay,
		removeDay,
		addTrack,
		renameTrack,
		removeTrack,
		refreshTypes: () => typesList.reload(),
		insertType: typesList.insert,
	}
}

export type ScheduleBuilder = ReturnType<typeof useScheduleBuilder>

const startMinutesOf = (time: string) => startMinutes({ start_time: time } as ScheduleItem)
