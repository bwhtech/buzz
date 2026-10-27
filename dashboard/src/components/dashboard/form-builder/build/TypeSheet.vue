<script setup lang="ts">
import { BottomSheet, TextInput } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { filterTypeGroups } from "../fieldTypes"

export interface TypeGroup {
	group: string
	options: { label: string; value: string; icon: string }[]
}

const props = defineProps<{ groups: TypeGroup[]; current: string }>()
const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ pick: [string] }>()

const query = ref("")
watch(open, (isOpen) => isOpen || (query.value = ""))
const matches = computed(() => filterTypeGroups(props.groups, query.value))

function pick(fieldtype: string) {
	open.value = false
	emit("pick", fieldtype)
}
</script>

<template>
	<BottomSheet v-model:open="open" title="Turn into">
		<div class="flex flex-col gap-3 px-2 pb-8">
			<div class="px-2">
				<TextInput
					v-model="query"
					size="lg"
					placeholder="Search field types"
					aria-label="Search field types"
				>
					<template #prefix><span class="lucide-search size-4 text-ink-gray-5" /></template>
				</TextInput>
			</div>
			<section v-for="{ group, options } in matches" :key="group" class="flex flex-col">
				<h3 class="px-3 pb-1 text-p-sm font-medium text-ink-gray-5">{{ group }}</h3>
				<button
					v-for="option in options"
					:key="option.value"
					type="button"
					class="flex min-h-12 items-center gap-3 rounded-5 px-3 text-left text-[15px] text-ink-gray-8 transition-colors duration-150 active:bg-surface-gray-3"
					:aria-pressed="option.value === current"
					@click="pick(option.value)"
				>
					<span :class="[option.icon, 'size-[18px] shrink-0 text-ink-gray-5']" aria-hidden="true" />
					<span class="flex-1">{{ option.label }}</span>
					<span
						v-if="option.value === current"
						class="lucide-check size-[18px] text-ink-gray-8"
						aria-hidden="true"
					/>
				</button>
			</section>
			<p v-if="!matches.length" class="py-6 text-center text-p-sm text-ink-gray-5">
				No field type matches “{{ query }}”
			</p>
		</div>
	</BottomSheet>
</template>
