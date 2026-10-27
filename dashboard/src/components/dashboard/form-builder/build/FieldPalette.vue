<script setup lang="ts">
import { TextInput } from "frappe-ui"
import { computed, ref } from "vue"

import { fieldMenu, type MenuItem } from "../fieldTypes"

const props = defineProps<{ formDoctype: string }>()
const emit = defineEmits<{ pick: [MenuItem]; dragstart: [MenuItem, DragEvent] }>()

const query = ref("")
const groups = computed(() => fieldMenu(props.formDoctype, query.value))
</script>

<template>
	<div class="flex h-full flex-col">
		<div class="p-3">
			<TextInput v-model="query" placeholder="Search fields" aria-label="Search fields">
				<template #prefix
					><span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true"
				/></template>
			</TextInput>
		</div>
		<div class="flex-1 space-y-3 overflow-y-auto px-3 pb-4">
			<section v-for="group in groups" :key="group.group">
				<h3 class="px-2 pb-1 text-p-xs font-medium text-ink-gray-5">{{ group.group }}</h3>
				<button
					v-for="item in group.items"
					:key="item.key"
					type="button"
					draggable="true"
					class="flex w-full items-center gap-2.5 rounded-5 px-2 py-1.5 text-left transition-colors duration-150 active:scale-[0.98] [@media(hover:hover)]:hover:bg-surface-gray-2"
					@click="emit('pick', item)"
					@dragstart="emit('dragstart', item, $event)"
				>
					<span :class="[item.icon, 'size-4 shrink-0 text-ink-gray-6']" aria-hidden="true" />
					<span class="min-w-0 flex-1">
						<span class="block text-p-sm text-ink-gray-8">{{ item.label }}</span>
						<span v-if="item.hint" class="block truncate text-p-xs text-ink-gray-5">{{
							item.hint
						}}</span>
					</span>
				</button>
			</section>
		</div>
	</div>
</template>
