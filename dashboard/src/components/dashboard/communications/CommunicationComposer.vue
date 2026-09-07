<script setup lang="ts">
import { Button, Select } from "frappe-ui"
import { Editor, EditorContent, EditorFixedMenu } from "frappe-ui/editor"
import { computed, ref } from "vue"

import type { CommunicationDraft } from "@/types"
import { audienceOptions, hasText } from "@/utils/communicationText"
import { proposalEditorExtensions, proposalEditorToolbar } from "@/utils/proposalEditor"

const props = defineProps<{ canWrite: boolean; sending: boolean }>()
const draft = defineModel<CommunicationDraft>({ required: true })
const emit = defineEmits<{ advanced: []; send: [] }>()

// Once the box has been touched the actions stay: a blur to reach the Advanced button
// must not fold them away under the pointer.
const touched = ref(false)
const showActions = computed(() => touched.value || hasText(draft.value.message))
const canSend = computed(() => props.canWrite && hasText(draft.value.message) && !props.sending)
</script>

<template>
	<section
		class="composer rounded-8 border border-outline-gray-2 bg-surface-white focus-within:border-outline-gray-4"
	>
		<p class="flex flex-wrap items-center gap-2 px-4 pt-4 text-base text-ink-gray-7">
			Send an announcement to your
			<Select
				v-model="draft.audience"
				size="sm"
				class="w-fit"
				aria-label="Recipients"
				:options="audienceOptions"
				:disabled="!canWrite"
			/>
		</p>

		<Editor
			v-model="draft.message"
			:extensions="proposalEditorExtensions"
			:editable="canWrite"
			placeholder="Write your message…"
			@focus="touched = true"
		>
			<EditorContent class="prose prose-sm min-h-[7rem] max-w-none px-4 py-3 text-ink-gray-8" />
			<!-- Arrives once and stays: the actions turning up is the confirmation that the box
			     took focus, so they rise in rather than pop, and never fold away under the pointer. -->
			<div
				v-if="showActions"
				class="composer-actions flex items-center gap-2 border-t border-outline-gray-1 p-2"
			>
				<EditorFixedMenu :items="proposalEditorToolbar" class="min-w-0 flex-1 overflow-x-auto" />
				<Button label="Advanced" icon-left="lucide-sliders-horizontal" @click="emit('advanced')" />
				<Button
					variant="solid"
					label="Send"
					icon-left="lucide-send"
					:disabled="!canSend"
					:loading="sending"
					@click="emit('send')"
				/>
			</div>
		</Editor>
	</section>
</template>

<style scoped>
.composer {
	--ease-out: cubic-bezier(0.23, 1, 0.32, 1);
	transition: border-color 150ms var(--ease-out);
}

.composer-actions {
	transition:
		opacity 160ms var(--ease-out),
		transform 160ms var(--ease-out);
}

@starting-style {
	.composer-actions {
		opacity: 0;
		transform: translateY(4px);
	}
}

/* Gentler, not none: the fade still says the row arrived, nothing travels. */
@media (prefers-reduced-motion: reduce) {
	@starting-style {
		.composer-actions {
			transform: none;
		}
	}
}
</style>
