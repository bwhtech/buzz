<script setup lang="ts">
import { badgeDotClass } from "@/utils/badgeTheme"
import { REQUEST_VIEWS, type RequestView } from "@/utils/requestStatus"

defineProps<{
	stats: { view: RequestView; label: string; count: number }[]
	active: RequestView | "all"
}>()
const emit = defineEmits<{ pick: [view: RequestView] }>()
</script>

<template>
	<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
		<button
			v-for="stat in stats"
			:key="stat.view"
			type="button"
			:aria-pressed="active === stat.view"
			class="flex flex-col gap-1.5 rounded-6 border bg-surface-base px-4 py-3.5 text-left transition-[border-color,box-shadow] duration-150 ease-out hover:border-outline-gray-3 motion-reduce:transition-none"
			:class="active === stat.view ? 'border-outline-gray-4 shadow-sm' : 'border-outline-gray-2'"
			@click="emit('pick', stat.view)"
		>
			<span class="flex items-center gap-1.5 text-sm text-ink-gray-5">
				<span
					class="size-1.5 shrink-0 rounded-full"
					:class="badgeDotClass(REQUEST_VIEWS[stat.view].theme)"
					aria-hidden="true"
				/>
				{{ stat.label }}
			</span>
			<span class="text-2xl font-semibold tabular-nums text-ink-gray-9">{{ stat.count }}</span>
		</button>
	</div>
</template>
