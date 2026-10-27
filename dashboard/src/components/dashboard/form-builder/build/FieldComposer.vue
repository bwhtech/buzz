<script setup lang="ts">
import { computed, ref, watch } from "vue"

import { fieldMenu, type MenuItem } from "../fieldTypes"

const props = defineProps<{ formDoctype: string }>()
const emit = defineEmits<{ pick: [MenuItem] }>()

const text = ref("")
const active = ref(0)
const input = ref<HTMLInputElement | null>(null)

// "/" opens the menu; any other text becomes a short text question on Enter.
const isSearching = computed(() => text.value.startsWith("/"))
const groups = computed(() =>
	isSearching.value ? fieldMenu(props.formDoctype, text.value.slice(1)) : [],
)
const items = computed(() => groups.value.flatMap((group) => group.items))
watch(text, () => (active.value = 0))

function pick(item: MenuItem) {
	emit("pick", item)
	text.value = ""
}

function onKeydown(event: KeyboardEvent) {
	if (isSearching.value && ["ArrowDown", "ArrowUp"].includes(event.key)) {
		event.preventDefault()
		const step = event.key === "ArrowDown" ? 1 : -1
		active.value = (active.value + step + items.value.length) % items.value.length
	} else if (event.key === "Enter" && text.value.trim()) {
		event.preventDefault()
		if (!isSearching.value)
			pick({
				key: "Data",
				label: "",
				icon: "",
				hint: "",
				fields: [{ fieldtype: "Data", label: text.value.trim() }],
			})
		else if (items.value[active.value]) pick(items.value[active.value])
	} else if (event.key === "Escape") {
		text.value = ""
	}
}

defineExpose({ focus: () => input.value?.focus() })
</script>

<template>
	<div class="relative">
		<div
			class="flex items-center gap-3 rounded-6 px-3 py-2.5 text-ink-gray-4 focus-within:bg-surface-gray-1"
		>
			<span class="lucide-plus size-4" aria-hidden="true" />
			<input
				ref="input"
				v-model="text"
				class="min-w-0 flex-1 border-0 bg-transparent p-0 text-p-base text-ink-gray-8 outline-none placeholder:text-ink-gray-4 focus:ring-0"
				placeholder="Type a question, or / for field types"
				aria-label="Add a field"
				role="combobox"
				:aria-expanded="isSearching"
				@keydown="onKeydown"
				@blur="text.startsWith('/') && (text = '')"
			/>
		</div>
		<div
			v-if="isSearching"
			class="absolute left-0 top-full z-20 mt-1 max-h-80 w-72 overflow-y-auto rounded-8 bg-surface-modal p-1 shadow-xl ring-1 ring-outline-gray-1"
			role="listbox"
		>
			<p v-if="!items.length" class="px-2.5 py-2 text-p-sm text-ink-gray-5">No field matches</p>
			<template v-for="group in groups" :key="group.group">
				<p class="px-2.5 pb-1 pt-2 text-p-xs font-medium text-ink-gray-5">{{ group.group }}</p>
				<button
					v-for="item in group.items"
					:key="item.key"
					type="button"
					role="option"
					:aria-selected="items[active] === item"
					class="flex w-full items-center gap-2 rounded-5 px-2.5 py-1.5 text-left text-p-sm text-ink-gray-8"
					:class="{ 'bg-surface-gray-3': items[active] === item }"
					@mousedown.prevent="pick(item)"
					@mouseenter="active = items.indexOf(item)"
				>
					<span :class="[item.icon, 'size-4 text-ink-gray-5']" aria-hidden="true" />
					<span class="flex-1">{{ item.label }}</span>
					<span v-if="item.fields.length > 1" class="text-p-xs text-ink-gray-4"
						>{{ item.fields.length }} fields</span
					>
				</button>
			</template>
		</div>
	</div>
</template>
