<script setup lang="ts">
import { Button, Popover } from "frappe-ui"
import { computed } from "vue"

import type { ChecklistItem } from "@/utils/eventValidation"

// Create, in the header or at the end of the form. A click with fields still missing
// lists them beside the button instead of saving.
const props = defineProps<{
	placement: "header" | "end"
	missing: ChecklistItem[]
	loading?: boolean
	wide?: boolean
}>()
const showMissing = defineModel<boolean>("showMissing", { default: false })
const emit = defineEmits<{ create: [] }>()

const atEnd = computed(() => props.placement === "end")
const open = computed({
	get: () => showMissing.value && props.missing.length > 0,
	set: (value: boolean) => (showMissing.value = value),
})
</script>

<template>
	<Popover
		v-model:open="open"
		:class="wide && 'w-full'"
		trigger="manual"
		:side="atEnd ? 'top' : 'bottom'"
		:align="wide ? 'center' : 'end'"
		:offset="8"
	>
		<template #trigger>
			<!-- Never disabled: the click is what explains what is missing. -->
			<Button
				variant="solid"
				:size="wide ? 'lg' : atEnd ? 'md' : 'sm'"
				:label="atEnd ? __('Create event') : __('Create')"
				:loading="loading"
				:class="wide && 'w-full'"
				class="transition-transform duration-150 ease-out active:scale-[0.97] motion-reduce:transition-none"
				@click="emit('create')"
			/>
		</template>
		<div
			class="flex flex-col gap-2 p-3"
			:class="wide ? 'w-[calc(100vw-2rem)]' : 'w-[280px]'"
			role="status"
		>
			<p class="text-sm font-semibold text-ink-gray-9">{{ __("Add these to create the event") }}</p>
			<p
				v-for="item in missing"
				:key="item.label"
				class="flex items-center gap-2 text-sm text-ink-red-7"
			>
				<span class="lucide-circle size-3.5" aria-hidden="true" />{{ item.label }}
			</p>
		</div>
	</Popover>
</template>
