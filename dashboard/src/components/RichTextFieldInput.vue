<script setup lang="ts">
import { Editor, EditorContent, EditorFixedMenu } from "frappe-ui/editor"
import { computed } from "vue"

import { EMPTY_EDITOR_HTML, richTextExtensions, richTextToolbar } from "@/utils/richTextEditor"

defineProps<{ placeholder?: string }>()
const model = defineModel<string>()

const html = computed({
	get: () => model.value || "",
	set: (value: string) => {
		model.value = EMPTY_EDITOR_HTML.test(value) ? "" : value
	},
})
</script>

<template>
	<Editor v-model="html" :extensions="richTextExtensions" :placeholder="placeholder">
		<EditorFixedMenu
			:items="richTextToolbar"
			class="rounded-t-5 border border-b-0 border-outline-gray-2 px-2 py-1"
		/>
		<EditorContent
			class="prose-sm py-2 px-3 min-h-[8rem] border border-outline-gray-2 hover:border-outline-gray-3 rounded-b-5 bg-surface-gray-3"
		/>
	</Editor>
</template>
