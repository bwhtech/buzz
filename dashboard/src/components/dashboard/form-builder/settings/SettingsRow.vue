<script setup lang="ts">
withDefaults(
	defineProps<{
		title: string
		description?: string
		icon: string
		tone?: keyof typeof TONES
		stacked?: boolean
	}>(),
	{ description: undefined, tone: "gray" },
)

const slots = defineSlots<{ default?(): unknown; below?(): unknown }>()
</script>

<script lang="ts">
const TONES = {
	gray: "bg-surface-gray-2 text-ink-gray-6",
	blue: "bg-surface-blue-1 text-ink-blue-6",
	amber: "bg-surface-amber-1 text-ink-amber-6",
	green: "bg-surface-green-1 text-ink-green-6",
	violet: "bg-surface-violet-1 text-ink-violet-7",
}
</script>

<template>
	<!-- Control to the right on wide screens; `below` holds editors that need the full width. -->
	<div class="flex flex-col gap-3 px-4 py-3.5">
		<div
			class="flex flex-col gap-3"
			:class="{ 'sm:flex-row sm:items-center sm:justify-between sm:gap-6': !stacked }"
		>
			<div class="flex min-w-0 items-center gap-3">
				<span
					class="grid size-9 shrink-0 place-items-center rounded-4"
					:class="TONES[tone]"
					aria-hidden="true"
				>
					<span :class="[icon, 'size-4']" />
				</span>
				<div class="min-w-0">
					<div class="text-p-base font-medium text-ink-gray-9">{{ title }}</div>
					<div v-if="description" class="mt-0.5 text-p-sm text-ink-gray-5">{{ description }}</div>
				</div>
			</div>
			<div v-if="slots.default" class="shrink-0" :class="{ 'sm:w-[260px]': !stacked }">
				<slot />
			</div>
		</div>
		<slot name="below" />
	</div>
</template>
