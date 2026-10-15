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
const chipOpen = ref(false)

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
	<div
		ref="root"
		class="composer flex gap-3 rounded-5 px-3 py-2.5 ring-1"
		:class="toRecipients ? 'bg-surface-gray-2 ring-outline-gray-2' : 'ring-transparent'"
	>
		<Avatar
			v-if="!editing"
			size="md"
			:label="me?.full_name || me?.email || ''"
			:image="me?.user_image ?? undefined"
			class="mt-1 shrink-0"
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
					<EditorContent class="max-h-48 min-h-16 overflow-y-auto py-1 text-base text-ink-gray-8" />
					<!-- Always laid out, only revealed, so focusing the field never shifts the composer. -->
					<div
						class="composer-footer flex items-center gap-2 pt-1"
						:data-shown="editing || focused || chipOpen || !isEmpty || toRecipients || undefined"
					>
						<AudienceChip
							v-if="canEmail && !editing"
							v-model="toRecipients"
							v-model:open="chipOpen"
							:recipients="recipients!"
							:recipients-label="recipientsLabel!"
						/>
						<div class="ml-auto flex items-center gap-2">
							<Button v-if="editing" variant="ghost" label="Cancel" @click="emit('cancel')" />
							<Button
								variant="solid"
								:label="editing ? 'Save' : toRecipients ? 'Send email' : 'Comment'"
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
.composer {
	transition:
		background-color 200ms ease,
		box-shadow 200ms ease;
}

.composer-footer {
	opacity: 0;
	visibility: hidden;
	transform: translateY(2px);
	transition:
		opacity 160ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 160ms cubic-bezier(0.23, 1, 0.32, 1),
		visibility 0s 160ms;
}

.composer-footer[data-shown] {
	opacity: 1;
	visibility: visible;
	transform: none;
	transition:
		opacity 160ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}

@media (prefers-reduced-motion: reduce) {
	.composer-footer {
		transform: none;
	}
}
</style>
