<script setup lang="ts">
import { useFocusWithin } from "@vueuse/core"
import { Avatar, Button } from "frappe-ui"
import { CommentKit, Editor, EditorContent } from "frappe-ui/editor"
import { computed, ref, watch } from "vue"

import { userResource } from "@/data/user"
import type { TeamMember } from "@/types"

import AudienceChip, { type Recipient } from "./AudienceChip.vue"
import { mentionSuggestion } from "./mentionSuggestion"

const props = defineProps<{
	members: TeamMember[]
	// Offered as "Email <recipientsLabel>" when the record has someone outside the team.
	recipients?: Recipient[]
	recipientsLabel?: string
	loading?: boolean
	editing?: boolean
}>()

const emit = defineEmits<{ submit: [content: string, toRecipients: boolean]; cancel: [] }>()

const draft = defineModel<string>({ default: "" })
const toRecipients = ref(false)

// Emailing is opted into per note, so the choice clears once the draft has been posted.
watch(draft, (value) => !value && (toRecipients.value = false))

const root = ref<HTMLElement>()
const { focused } = useFocusWithin(root)

const me = computed(() => userResource.data)
const canEmail = computed(() => Boolean(props.recipients?.length && props.recipientsLabel))

const extensions = [
	CommentKit.configure({ image: false, video: false, attachment: false, mention: {} }),
	mentionSuggestion(() => props.members),
]

function submit(isEmpty: boolean) {
	if (!isEmpty && !props.loading) emit("submit", draft.value, toRecipients.value)
}
</script>

<template>
	<div ref="root" class="flex gap-3">
		<Avatar
			v-if="!editing"
			size="md"
			:label="me?.full_name || me?.email || ''"
			:image="me?.user_image ?? undefined"
			class="mt-1.5 shrink-0"
		/>
		<Editor
			v-model="draft"
			:extensions="extensions"
			:autofocus="editing"
			:placeholder="
				toRecipients ? `Write to the ${recipientsLabel}…` : 'Add a note for the team… @ to mention'
			"
		>
			<template #default="{ isEmpty }">
				<div
					class="min-w-0 flex-1"
					@keydown.meta.enter="submit(isEmpty)"
					@keydown.ctrl.enter="submit(isEmpty)"
				>
					<EditorContent
						class="max-h-48 min-h-9 overflow-y-auto py-2 text-base text-ink-gray-8"
						:class="toRecipients && 'rounded-6 bg-surface-blue-1/40 px-2'"
					/>
					<div
						v-if="editing || focused || !isEmpty || toRecipients"
						class="composer-footer flex items-center gap-2 pt-1"
					>
						<AudienceChip
							v-if="canEmail && !editing"
							v-model="toRecipients"
							:recipients="recipients!"
							:recipients-label="recipientsLabel!"
						/>
						<div class="ml-auto flex items-center gap-2">
							<Button
								v-if="editing"
								size="sm"
								variant="ghost"
								label="Cancel"
								@click="emit('cancel')"
							/>
							<Button
								size="sm"
								variant="solid"
								:label="editing ? 'Save' : toRecipients ? 'Send' : 'Comment'"
								:icon-left="toRecipients ? 'lucide-send' : undefined"
								:disabled="isEmpty"
								:loading="loading"
								@click="submit(isEmpty)"
							/>
						</div>
					</div>
				</div>
			</template>
		</Editor>
	</div>
</template>

<style scoped>
.composer-footer {
	transition: opacity 180ms cubic-bezier(0.23, 1, 0.32, 1);
}

@starting-style {
	.composer-footer {
		opacity: 0;
	}
}
</style>
