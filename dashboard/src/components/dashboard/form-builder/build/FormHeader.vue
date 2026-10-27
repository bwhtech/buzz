<script setup lang="ts">
import { dayjs } from "frappe-ui"
import { computed } from "vue"

import { useEventDoc } from "@/data/events"
import { timeLabel12Hour } from "@/utils/dateLabels"

import type { BuzzFormDoc } from "../useFormBuilder"

const form = defineModel<BuzzFormDoc>({ required: true })
const props = defineProps<{ readonly?: boolean }>()

const event = useEventDoc(() => form.value.event)

const schedule = computed(() => {
	const doc = event.doc
	if (!doc?.start_date) return []
	const times = [doc.start_time, doc.end_time].filter(Boolean).map((time) => timeLabel12Hour(time!))
	const time = times.length
		? [times.join(" – "), doc.time_zone_label].filter(Boolean).join(" ")
		: ""
	return [dayjs(doc.start_date).format("ddd, MMM D"), time].filter(Boolean)
})

const blurOnEnter = (keydown: KeyboardEvent) => (keydown.target as HTMLElement).blur()
</script>

<template>
	<div class="mb-4 flex flex-col gap-2.5 border-b border-outline-gray-1 pb-6">
		<div class="flex flex-wrap items-center gap-2 text-p-sm text-ink-gray-5">
			<span
				class="grid size-5 place-items-center rounded-3 bg-surface-gray-7 text-ink-base"
				aria-hidden="true"
			>
				<span class="lucide-calendar size-3" />
			</span>
			<span class="font-medium text-ink-gray-8">{{ event.doc?.title }}</span>
			<template v-for="part in schedule" :key="part">
				<span class="text-ink-gray-3" aria-hidden="true">·</span>
				<span>{{ part }}</span>
			</template>
		</div>
		<textarea
			v-model="form.title"
			rows="1"
			:readonly="props.readonly"
			placeholder="Untitled form"
			aria-label="Form name"
			class="mt-1.5 w-full resize-none overflow-hidden border-0 bg-transparent p-0 text-[26px] md:text-[30px] font-semibold leading-[1.25] tracking-[-0.02em] text-ink-gray-9 outline-none [field-sizing:content] [text-wrap:balance] placeholder:text-ink-gray-4 focus:ring-0"
			@keydown.enter.prevent="blurOnEnter"
			@click.stop
		/>
		<input
			v-model="form.description"
			:readonly="props.readonly"
			placeholder="Add a short intro"
			aria-label="Form description"
			class="w-full border-0 bg-transparent p-0 text-[15px] leading-[1.55] text-ink-gray-6 outline-none placeholder:text-ink-gray-4 focus:ring-0"
			@click.stop
		/>
	</div>
</template>
