<script setup lang="ts">
export interface RailItem {
	value: string
	label: string
	description: string
	icon: string
	count: number
}

defineProps<{ items: RailItem[] }>()
const scope = defineModel<string>({ required: true })
</script>

<template>
	<nav
		class="flex w-60 flex-col gap-0.5 rounded-5 border border-outline-gray-2 bg-surface-base p-1.5"
		aria-label="Registration forms"
	>
		<span class="px-2 pb-1.5 pt-1 text-sm text-ink-gray-5">Questions</span>
		<button
			v-for="item in items"
			:key="item.value"
			type="button"
			class="flex items-center gap-2.5 rounded-3 p-2 text-left transition-colors duration-150 active:scale-[0.98] motion-reduce:transition-none"
			:class="
				scope === item.value ? 'bg-surface-gray-2' : '[@media(hover:hover)]:hover:bg-surface-gray-1'
			"
			:aria-current="scope === item.value ? 'true' : undefined"
			@click="scope = item.value"
		>
			<span
				class="grid size-8 shrink-0 place-items-center rounded-3 border text-ink-gray-7"
				:class="
					scope === item.value
						? 'border-outline-gray-2 bg-surface-base'
						: 'border-transparent bg-surface-gray-2'
				"
			>
				<span :class="item.icon" class="size-4" aria-hidden="true" />
			</span>
			<span class="flex min-w-0 flex-1 flex-col gap-0.5">
				<span class="text-base font-medium text-ink-gray-9">{{ item.label }}</span>
				<span class="truncate text-sm text-ink-gray-5">{{ item.description }}</span>
			</span>
			<span class="text-sm tabular-nums text-ink-gray-5">{{ item.count }}</span>
		</button>
	</nav>
</template>
