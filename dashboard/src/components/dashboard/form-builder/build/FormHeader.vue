<script setup lang="ts">
import { dayjs } from "frappe-ui"
import { computed, ref } from "vue"

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

const emit = defineEmits<{ leaveDown: [] }>()
const title = ref<HTMLTextAreaElement | null>(null)
const description = ref<HTMLInputElement | null>(null)

defineExpose({ focus: () => description.value?.focus() })
</script>

<template>
	<div class="mb-4 flex flex-col gap-2.5 border-b border-outline-gray-1 pb-6">
		<div class="flex flex-wrap items-center gap-2 text-p-sm text-ink-gray-5">
			<span class="font-medium text-ink-gray-8">{{ event.doc?.title }}</span>
			<template v-for="part in schedule" :key="part">
				<span class="text-ink-gray-3" aria-hidden="true">·</span>
				<span>{{ part }}</span>
			</template>
		</div>
		<textarea
			ref="title"
			v-model="form.title"
			rows="1"
			:readonly="props.readonly"
			placeholder="Untitled form"
			aria-label="Form name"
			class="mt-1.5 w-full resize-none overflow-hidden border-0 bg-transparent p-0 text-[26px] md:text-[30px] font-semibold leading-[1.25] tracking-[-0.02em] text-ink-gray-9 outline-none [field-sizing:content] [text-wrap:balance] placeholder:text-ink-gray-4 focus:ring-0"
			@keydown.enter.prevent="description?.focus()"
			@keydown.down.prevent="description?.focus()"
			@click.stop
		/>
		<input
			v-if="!props.readonly || form.description"
			ref="description"
			v-model="form.description"
			:readonly="props.readonly"
			placeholder="Add a short intro"
			aria-label="Form description"
			class="w-full border-0 bg-transparent p-0 text-[15px] leading-[1.55] text-ink-gray-6 outline-none placeholder:text-ink-gray-4 focus:ring-0"
			@keydown.up.prevent="title?.focus()"
			@keydown.down.prevent="emit('leaveDown')"
			@keydown.enter.prevent="emit('leaveDown')"
			@click.stop
		/>
	</div>
</template>
