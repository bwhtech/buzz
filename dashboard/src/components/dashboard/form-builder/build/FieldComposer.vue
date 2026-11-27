<script setup lang="ts">
import { Combobox } from "frappe-ui"
import { computed, nextTick, ref } from "vue"

import { fieldMenu, type MenuItem } from "../fieldTypes"

const props = defineProps<{ formDoctype: string }>()
const emit = defineEmits<{ pick: [MenuItem]; leaveUp: [] }>()

const query = ref("")
const isOpen = ref(false)
const combobox = ref<InstanceType<typeof Combobox> | null>(null)

// Typed text can become a short text question; "/" only searches the field types.
const isSlashQuery = computed(() => query.value.startsWith("/"))
const groups = computed(() =>
	fieldMenu(props.formDoctype, isSlashQuery.value ? query.value.slice(1) : query.value),
)
const items = computed(() => groups.value.flatMap((group) => group.items))

const addTypedQuestion = {
	type: "custom" as const,
	key: "typed-question",
	label: "Add as a short text question",
	icon: "lucide-plus",
	condition: () => Boolean(query.value.trim()) && !isSlashQuery.value,
	onClick: () =>
		pick({
			key: "Data",
			label: "",
			icon: "",
			fields: [{ fieldtype: "Data", label: query.value.trim() }],
		}),
}

const options = computed(() => [
	{ group: "Question", hideLabel: true, options: [addTypedQuestion] },
	...groups.value.map((group) => ({
		group: group.group,
		options: group.items.map((item) => ({
			label: item.label,
			value: item.key,
			icon: item.icon,
			description: item.fields.length > 1 ? `${item.fields.length} fields` : undefined,
		})),
	})),
])

function pick(item: MenuItem | undefined) {
	if (item) emit("pick", item)
	isOpen.value = false
	void nextTick().then(() => (query.value = ""))
}

function onKeydown(event: KeyboardEvent) {
	if (event.key === "ArrowUp" && !isOpen.value) emit("leaveUp")
}

defineExpose({ focus: () => combobox.value?.focus() })
</script>

<template>
	<Combobox
		ref="combobox"
		v-model:query="query"
		v-model:open="isOpen"
		:model-value="null"
		:options="options"
		:filterable="false"
		class="w-full"
		variant="ghost"
		placeholder="Add question: click to pick a type, or type and press Enter"
		aria-label="Add a field"
		empty-text="No field matches"
		@update:model-value="(key) => pick(items.find((item) => item.key === key))"
		@keydown="onKeydown"
	>
		<template #prefix>
			<span class="lucide-plus size-4 text-ink-gray-5" aria-hidden="true" />
		</template>
	</Combobox>
</template>
