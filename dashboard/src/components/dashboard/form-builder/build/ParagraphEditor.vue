<script setup lang="ts">
import { Editor, EditorBubbleMenu, EditorContent } from "frappe-ui/editor"
import { computed } from "vue"

import { EMPTY_EDITOR_HTML, inlineTextToolbar, richTextExtensions } from "@/utils/richTextEditor"

const text = defineModel<string | null | undefined>({ required: true })
defineProps<{ contentClass?: string }>()

const html = computed({
	get: () => text.value || "",
	set: (value: string) => (text.value = EMPTY_EDITOR_HTML.test(value) ? "" : value),
})
</script>

<template>
	<Editor v-model="html" :extensions="richTextExtensions" placeholder="Write something…">
		<EditorBubbleMenu :items="inlineTextToolbar" />
		<EditorContent :class="['prose prose-sm max-w-none text-ink-gray-7', contentClass]" />
	</Editor>
</template>
