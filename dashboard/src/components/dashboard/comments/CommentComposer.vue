<script setup lang="ts">
import { Button, TabButtons } from "frappe-ui"
import { CommentKit, Editor, EditorContent } from "frappe-ui/editor"
import { computed, ref, watch } from "vue"

import type { EmailCopies } from "@/data/comments"
import type { TeamMember } from "@/types"

import { mentionSuggestion } from "./mentionSuggestion"
import RecipientRow from "./RecipientRow.vue"

export type Recipient = { name: string; email: string }

const props = defineProps<{
	members: TeamMember[]
	// The record's outside party, such as its speakers; with them the composer can email.
	recipients?: Recipient[]
	// The address emails are sent from.
	sender?: string | null
	loading?: boolean
	editing?: boolean
}>()

const emit = defineEmits<{
	submit: [content: string, toRecipients: boolean, copies: EmailCopies]
	cancel: []
}>()

const draft = defineModel<string>({ default: "" })
const mode = ref<"note" | "email">("note")
const cc = ref<string[]>([])
const bcc = ref<string[]>([])
const showCc = ref(false)
const showBcc = ref(false)

const canEmail = computed(() => Boolean(props.recipients?.length) && !props.editing)
const emailing = computed(() => canEmail.value && mode.value === "email")
const firstNames = computed(() =>
	(props.recipients ?? []).map((recipient) => recipient.name.split(" ")[0]).join(" and "),
)
const hint = computed(() =>
	emailing.value
		? props.sender
			? `Sends from ${props.sender}`
			: "Emails the speakers"
		: "Visible to organizers only",
)

const modes = [
	{ label: "Note", value: "note", iconLeft: "lucide-message-square" },
	{ label: "Email", value: "email", iconLeft: "lucide-mail" },
]

const extensions = [
	CommentKit.configure({ image: false, video: false, attachment: false, mention: {} }),
	mentionSuggestion(() => props.members),
]

// Mode and copies are chosen per message: the parent clears the draft once it is sent.
const sent = ref(false)
watch(draft, (value) => {
	if (value || !sent.value) return
	sent.value = false
	mode.value = "note"
	cc.value = []
	bcc.value = []
	showCc.value = showBcc.value = false
})

function submit(isEmpty: boolean) {
	if (isEmpty || props.loading) return
	sent.value = true
	emit("submit", draft.value, emailing.value, { cc: cc.value, bcc: bcc.value })
}
</script>

<template>
	<Editor
		v-model="draft"
		:extensions="extensions"
		:autofocus="editing"
		:placeholder="emailing ? `Write to ${firstNames}…` : 'Add a note… @ to mention an organizer'"
	>
		<template #default="{ editor, isEmpty }">
			<div
				class="composer overflow-hidden rounded-5 bg-surface-base"
				@keydown.meta.enter="submit(isEmpty)"
				@keydown.ctrl.enter="submit(isEmpty)"
			>
				<div v-if="canEmail" class="flex items-center gap-2 px-3 pt-3">
					<TabButtons v-model="mode" :options="modes" />
					<span class="ml-auto truncate text-sm text-ink-gray-5">{{ hint }}</span>
				</div>

				<div
					v-if="emailing"
					class="reveal mx-0.5 flex flex-col border-b border-outline-gray-1 py-1.5"
				>
					<RecipientRow label="To" :fixed="recipients!.map((recipient) => recipient.name)">
						<Button v-if="!showCc" variant="ghost" size="sm" label="Cc" @click="showCc = true" />
						<Button v-if="!showBcc" variant="ghost" size="sm" label="Bcc" @click="showBcc = true" />
					</RecipientRow>
					<RecipientRow v-if="showCc" v-model="cc" class="reveal" label="Cc" />
					<RecipientRow v-if="showBcc" v-model="bcc" class="reveal" label="Bcc" />
				</div>

				<!-- On a phone typed text is lifted to 16px (index.css) so iOS does not zoom on focus. -->
				<EditorContent
					class="max-h-48 min-h-[4.5rem] overflow-y-auto px-3.5 pt-3 pb-1 text-base leading-[1.55] text-ink-gray-8"
				/>

				<div class="flex items-center gap-1 px-3 pt-2 pb-3">
					<Button
						v-if="!editing"
						variant="ghost"
						size="sm"
						icon="lucide-at-sign"
						aria-label="Mention an organizer"
						@click="editor?.chain().focus().insertContent(' @').run()"
					/>
					<div class="ml-auto flex items-center gap-1">
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
							:label="editing ? 'Save' : emailing ? 'Send email' : 'Comment'"
							:disabled="isEmpty"
							:loading="loading"
							@click="submit(isEmpty)"
						/>
					</div>
				</div>
			</div>
		</template>
	</Editor>
</template>

<style scoped>
/* Layered so the box lifts off the feed: a hairline edge in place of a border, a tight
   contact shadow, and a wide soft one. Typing deepens it a step. */
.composer {
	box-shadow:
		0 0 0 0.5px rgb(0 0 0 / 0.08),
		0 1px 2px rgb(0 0 0 / 0.04),
		0 6px 16px -4px rgb(0 0 0 / 0.08),
		0 16px 40px -12px rgb(0 0 0 / 0.1);
	transition: box-shadow 200ms ease;
}

.composer:focus-within {
	box-shadow:
		0 0 0 0.5px rgb(0 0 0 / 0.12),
		0 1px 2px rgb(0 0 0 / 0.05),
		0 8px 20px -4px rgb(0 0 0 / 0.1),
		0 20px 48px -12px rgb(0 0 0 / 0.14);
}
</style>
