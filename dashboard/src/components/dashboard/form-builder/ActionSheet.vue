<script setup lang="ts">
import { BottomSheet } from "frappe-ui"

export interface SheetAction {
	label: string
	icon: string
	onClick: () => void
	disabled?: boolean
	theme?: "red"
}

defineProps<{ title?: string; actions: SheetAction[] }>()
const open = defineModel<boolean>("open", { required: true })

function run(action: SheetAction) {
	open.value = false
	action.onClick()
}
</script>

<template>
	<BottomSheet v-model:open="open" :title="title">
		<div class="flex flex-col px-2 pb-6">
			<button
				v-for="action in actions"
				:key="action.label"
				type="button"
				class="flex min-h-12 items-center gap-3 rounded-5 px-3 text-left text-[15px] transition-colors duration-150 active:bg-surface-gray-3 disabled:opacity-40"
				:class="action.theme === 'red' ? 'text-ink-red-4' : 'text-ink-gray-8'"
				:disabled="action.disabled"
				@click="run(action)"
			>
				<span :class="[action.icon, 'size-[18px] shrink-0']" aria-hidden="true" />
				{{ action.label }}
			</button>
		</div>
	</BottomSheet>
</template>
