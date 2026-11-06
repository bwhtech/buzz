<script setup lang="ts">
import { injectListboxRootContext } from "reka-ui"
import { nextTick, watch } from "vue"

// The palette highlights its first row as the query changes, but search rows land a
// moment later. Without a highlighted row, Enter and Tab have nothing to act on.
const props = defineProps<{ rowIds: string }>()
const listbox = injectListboxRootContext()

watch(
	() => props.rowIds,
	async () => {
		await nextTick()
		if (!listbox.highlightedElement.value?.isConnected) listbox.highlightFirstItem()
	},
)
</script>

<template>
	<span hidden />
</template>
