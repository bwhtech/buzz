<script setup lang="ts">
import { Button, Checkbox } from "frappe-ui"
import { CommentKit, Editor, EditorContent } from "frappe-ui/editor"
import { computed, ref, watch } from "vue"

import type { TeamMember } from "@/types"

const props = defineProps<{
	members: TeamMember[]
	loading?: boolean
	submitLabel?: string
	emailLabel?: string
}>()

const emit = defineEmits<{ submit: [content: string, emailRecipients: boolean]; cancel: [] }>()

const draft = defineModel<string>({ default: "" })
const emailRecipients = ref(false)

// Emailing is opted into per note, so the box clears once the draft has been posted.
watch(draft, (value) => !value && (emailRecipients.value = false))

// Mentions carry the user's email as `data-id`, which is what Frappe's extract_mentions reads.
const mentions = computed(() =>
	props.members.map((member) => ({ id: member.user, label: member.full_name || member.user })),
)

const extensions = [
	CommentKit.configure({
		mention: { items: mentions },
		image: false,
		video: false,
		attachment: false,
	}),
]

function submit() {
	emit("submit", draft.value, emailRecipients.value)
}
</script>

<template>
	<Editor v-model="draft" :extensions="extensions" placeholder="Add a comment… use @ to mention">
		<template #default="{ isEmpty }">
			<div
				class="rounded-6 border border-outline-gray-2 bg-surface-base focus-within:border-outline-gray-3"
			>
				<EditorContent
					class="max-h-56 min-h-16 overflow-y-auto px-3 py-2 text-base text-ink-gray-8"
				/>
				<div class="flex items-center gap-2 border-t border-outline-gray-1 px-2 py-1.5">
					<Checkbox v-if="emailLabel" v-model="emailRecipients" :label="emailLabel" size="sm" />
					<div class="ml-auto flex gap-2">
						<Button
							v-if="submitLabel"
							size="sm"
							variant="ghost"
							label="Cancel"
							@click="emit('cancel')"
						/>
						<Button
							size="sm"
							variant="solid"
							:label="submitLabel || 'Comment'"
							:disabled="isEmpty"
							:loading="loading"
							@click="submit"
						/>
					</div>
				</div>
			</div>
		</template>
	</Editor>
</template>
