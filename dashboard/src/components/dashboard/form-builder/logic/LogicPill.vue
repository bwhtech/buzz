<script setup lang="ts">
import { Dropdown } from "frappe-ui"

// "value" is a filled pill, "outline" a white one for grey panels, "word" reads as plain text, "join" is an outlined and/or toggle.
const props = withDefaults(
	defineProps<{
		label: string
		options?: { label: string; onClick: () => void }[]
		kind?: "value" | "outline" | "word" | "join" | "show" | "hide" | "require"
	}>(),
	{ options: undefined, kind: "value" },
)
defineEmits<{ click: [] }>()

const KINDS = {
	value: "bg-surface-gray-2 text-ink-gray-8 [@media(hover:hover)]:hover:bg-surface-gray-3",
	outline:
		"bg-surface-base text-ink-gray-8 ring-1 ring-inset ring-outline-gray-2 [@media(hover:hover)]:hover:bg-surface-gray-1",
	word: "text-ink-gray-6 [@media(hover:hover)]:hover:bg-surface-gray-2",
	join: "text-ink-gray-7 ring-1 ring-inset ring-outline-gray-2 [@media(hover:hover)]:hover:bg-surface-gray-2",
	show: "bg-surface-green-1 text-ink-green-6 [@media(hover:hover)]:hover:bg-surface-green-2",
	hide: "bg-surface-gray-2 text-ink-gray-8 [@media(hover:hover)]:hover:bg-surface-gray-3",
	require: "bg-surface-amber-1 text-ink-amber-6 [@media(hover:hover)]:hover:bg-surface-amber-2",
}
const CLASS =
	"inline-flex h-[26px] max-w-[240px] items-center rounded-3 px-2 text-p-base transition-colors duration-150"
</script>

<template>
	<Dropdown v-if="props.options" :options="props.options">
		<button type="button" :class="[CLASS, KINDS[props.kind]]">
			<span class="truncate">{{ props.label }}</span>
		</button>
	</Dropdown>
	<button v-else type="button" :class="[CLASS, KINDS[props.kind]]" @click="$emit('click')">
		<span class="truncate">{{ props.label }}</span>
	</button>
</template>
