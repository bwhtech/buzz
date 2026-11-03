<script setup lang="ts">
import { BottomSheet, TextInput } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { fieldMenu, type MenuItem } from "../fieldTypes"

const props = defineProps<{ formDoctype: string; stepName: string }>()
const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ pick: [MenuItem] }>()

const query = ref("")
const groups = computed(() => fieldMenu(props.formDoctype, query.value))
watch(open, (isOpen) => isOpen || (query.value = ""))

function pick(item: MenuItem) {
	open.value = false
	emit("pick", item)
}
</script>

<template>
	<BottomSheet v-model:open="open" title="Add field">
		<div class="flex flex-col gap-4 px-4 pb-8">
			<p v-if="stepName" class="-mt-2 text-center text-p-sm text-ink-gray-5">to {{ stepName }}</p>
			<TextInput v-model="query" size="lg" placeholder="Search fields" aria-label="Search fields">
				<template #prefix><span class="lucide-search size-4 text-ink-gray-5" /></template>
			</TextInput>
			<section v-for="group in groups" :key="group.group" class="flex flex-col gap-2">
				<h3 class="px-1 text-p-sm font-medium text-ink-gray-5">{{ group.group }}</h3>
				<div class="grid grid-cols-3 gap-2">
					<button
						v-for="item in group.items"
						:key="item.key"
						type="button"
						class="flex min-h-[76px] flex-col items-center justify-center gap-2 rounded-5 bg-surface-gray-1 px-2 text-center text-p-sm text-ink-gray-8 ring-1 ring-inset ring-outline-gray-1 transition-transform duration-150 active:scale-[0.97]"
						@click="pick(item)"
					>
						<span :class="[item.icon, 'size-5 text-ink-gray-6']" aria-hidden="true" />
						{{ item.label }}
					</button>
				</div>
			</section>
			<p v-if="!groups.length" class="py-6 text-center text-p-sm text-ink-gray-5">
				No field types match “{{ query }}”
			</p>
		</div>
	</BottomSheet>
</template>
