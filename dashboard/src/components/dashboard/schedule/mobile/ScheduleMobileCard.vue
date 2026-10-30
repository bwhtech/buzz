<script setup lang="ts">
import { Badge } from "frappe-ui"
import { computed } from "vue"

import { blockColors } from "../scheduleColors"
import { scheduleIcon } from "../scheduleIcons"
import { durationLabel } from "../scheduleLayout"
import type { ScheduleItem } from "../scheduleTypes"
import { useBuilder } from "../useScheduleBoard"
import ScheduleMobileCardActions from "./ScheduleMobileCardActions.vue"

const props = defineProps<{
	item: ScheduleItem
	conflict?: string
	actions?: boolean
	movable?: boolean
}>()
defineEmits<{ edit: []; press: [event: PointerEvent] }>()
const builder = useBuilder()

const details = computed(() => builder.itemDetails(props.item))
const colors = computed(() => blockColors(details.value.type?.color))
const clickSelf = (event: KeyboardEvent) => (event.currentTarget as HTMLElement).click()
const isSpan = computed(() => !props.item.track)
const speakers = computed(() => details.value.speakers.join(", "))
const icon = computed(() => scheduleIcon(details.value.type?.icon) || "lucide-calendar-clock")
const meta = computed(() => {
	const duration = durationLabel(props.item.duration)
	if (isSpan.value) return `All tracks · ${duration}`
	const type = details.value.type?.title ?? props.item.type
	return `${type} · ${builder.tracks.titleOf(props.item.track)} · ${duration}`
})
const cardStyle = computed(() => ({
	background: colors.value.background,
	borderColor: props.conflict ? "var(--outline-red-3)" : colors.value.border,
}))
</script>

<template>
	<div
		v-if="isSpan"
		:role="actions ? undefined : 'button'"
		:tabindex="actions ? undefined : 0"
		@keydown.enter="clickSelf"
		class="flex w-full items-center gap-2 rounded-5 bg-surface-gray-2 px-3 py-2.5 text-left text-p-sm text-ink-gray-7 transition-transform duration-100 active:scale-[0.98]"
	>
		<span :class="[icon, 'size-3.5 shrink-0']" aria-hidden="true" />
		<span class="min-w-0 flex-1 truncate font-medium">{{ details.title }}</span>
		<span class="whitespace-nowrap text-p-xs text-ink-gray-5">{{ meta }}</span>
		<Badge v-if="conflict" theme="red" size="sm" label="Overlap" />
		<ScheduleMobileCardActions
			v-if="actions"
			class="-my-1 -mr-1.5"
			:movable="movable"
			@edit="$emit('edit')"
			@press="$emit('press', $event)"
		/>
	</div>
	<div
		v-else
		:role="actions ? undefined : 'button'"
		:tabindex="actions ? undefined : 0"
		@keydown.enter="clickSelf"
		class="block w-full min-w-0 rounded-5 border px-3 py-2.5 text-left transition-transform duration-100 active:scale-[0.98]"
		:style="cardStyle"
	>
		<span class="flex items-start gap-2">
			<span class="min-w-0 flex-1">
				<span
					class="line-clamp-2 block text-p-base font-medium text-ink-gray-9 [overflow-wrap:anywhere]"
					>{{ details.title }}</span
				>
				<span class="mt-1 flex min-w-0 items-center gap-1.5 text-p-xs text-ink-gray-6">
					<span class="size-[7px] shrink-0 rounded-full" :style="{ background: colors.dot }" />
					<span class="truncate">{{ meta }}</span>
				</span>
				<span v-if="speakers" class="mt-0.5 block truncate text-p-xs text-ink-gray-5">{{
					speakers
				}}</span>
			</span>
			<Badge v-if="conflict" theme="red" size="sm" label="Overlap" />
			<ScheduleMobileCardActions
				v-if="actions"
				class="-my-1 -mr-1.5"
				:movable="movable"
				@edit="$emit('edit')"
				@press="$emit('press', $event)"
			/>
		</span>
	</div>
</template>
