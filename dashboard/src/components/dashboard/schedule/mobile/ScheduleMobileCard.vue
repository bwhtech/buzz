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

const resolved = computed(() => builder.resolve(props.item))
const colors = computed(() => blockColors(resolved.value.type?.color))
const tag = computed(() => (props.actions ? "div" : "button"))
const isSpan = computed(() => !props.item.room)
const speakers = computed(() => resolved.value.speakers.join(", "))
const icon = computed(() => scheduleIcon(resolved.value.type?.icon) || "lucide-calendar-clock")
const meta = computed(() => {
	const duration = durationLabel(props.item.duration)
	if (isSpan.value) return `All rooms · ${duration}`
	const type = resolved.value.type?.title ?? props.item.type
	return `${type} · ${builder.rooms.titleOf(props.item.room)} · ${duration}`
})
const cardStyle = computed(() => ({
	background: colors.value.background,
	borderColor: props.conflict ? "var(--outline-red-3)" : colors.value.border,
}))
</script>

<template>
	<component
		:is="tag"
		v-if="isSpan"
		:type="actions ? undefined : 'button'"
		class="flex w-full items-center gap-2 rounded-5 bg-surface-gray-2 px-3 py-2.5 text-left text-p-sm text-ink-gray-7 transition-transform duration-100 active:scale-[0.98]"
	>
		<span :class="[icon, 'size-3.5 shrink-0']" aria-hidden="true" />
		<span class="min-w-0 flex-1 truncate font-medium">{{ resolved.title }}</span>
		<span class="whitespace-nowrap text-p-xs text-ink-gray-5">{{ meta }}</span>
		<Badge v-if="conflict" theme="red" size="sm" label="Overlap" />
		<ScheduleMobileCardActions
			v-if="actions"
			class="-my-1 -mr-1.5"
			:movable="movable"
			@edit="$emit('edit')"
			@press="$emit('press', $event)"
		/>
	</component>
	<component
		:is="tag"
		v-else
		:type="actions ? undefined : 'button'"
		class="block w-full min-w-0 rounded-5 border px-3 py-2.5 text-left transition-transform duration-100 active:scale-[0.98]"
		:style="cardStyle"
	>
		<span class="flex items-start gap-2">
			<span class="min-w-0 flex-1">
				<span
					class="line-clamp-2 block text-p-base font-medium text-ink-gray-9 [overflow-wrap:anywhere]"
					>{{ resolved.title }}</span
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
	</component>
</template>
