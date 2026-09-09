<script setup lang="ts">
import { Button, DateTimePicker, FormControl, MultiSelect, Select, dayjsLocal } from "frappe-ui"
import { Editor, EditorContent, EditorFixedMenu } from "frappe-ui/editor"
import { computed, ref, watch } from "vue"

import {
	Drawer,
	DrawerClose,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import { useRecipientCount } from "@/data/communications"
import type { CommunicationDraft, CommunicationItem, EventCommunications } from "@/types"
import { audienceOptions, hasText } from "@/utils/communicationText"
import { richTextExtensions, richTextToolbar } from "@/utils/richTextEditor"

const props = defineProps<{
	event: string
	options: Pick<EventCommunications, "ticket_types" | "statuses"> | null
	// A sent message to read back; null means the drawer is composing.
	viewing: CommunicationItem | null
	canWrite: boolean
	sending: boolean
}>()
const open = defineModel<boolean>("open", { required: true })
const draft = defineModel<CommunicationDraft>("draft", { required: true })
const emit = defineEmits<{ send: [] }>()

const tierOptions = computed(() =>
	(props.options?.ticket_types || []).map((type) => ({
		value: type.name,
		label: type.title || type.name,
	})),
)
const statusOptions = computed(() =>
	(props.options?.statuses || []).map((status) => ({ value: status, label: status })),
)

const count = useRecipientCount(() => ({
	event: props.event,
	audience: draft.value.audience,
	ticket_types: draft.value.ticket_types.join(","),
	statuses: draft.value.statuses.join(","),
}))

// Scheduling is a mode of the footer rather than a field: most messages go out now, so
// the picker only appears once asked for, and clearing it sends now again.
const scheduling = ref(false)
watch(open, (isOpen) => isOpen && (scheduling.value = !!draft.value.scheduled_at))
const minSchedule = dayjsLocal().format("YYYY-MM-DD HH:mm:ss")

const canSend = computed(
	() =>
		props.canWrite &&
		hasText(draft.value.message) &&
		!props.sending &&
		(!scheduling.value || !!draft.value.scheduled_at),
)

function send() {
	if (!scheduling.value) draft.value.scheduled_at = ""
	emit("send")
}

const viewedFilters = computed(() => {
	const row = props.viewing
	if (!row) return ""
	const chosen = row.audience === "Guests" ? row.ticket_types : row.statuses
	if (!chosen) return `All ${row.audience.toLowerCase()}`
	const titles = new Map(tierOptions.value.map((option) => [option.value, option.label]))
	const filters = chosen
		.split(",")
		.map((value) => titles.get(value) || value)
		.join(", ")
	// "Speakers · Rejected" rather than "Rejected": the status alone does not say who.
	return `${row.audience} · ${filters}`
})
const viewedWhen = computed(() =>
	props.viewing
		? dayjsLocal(props.viewing.scheduled_at || props.viewing.creation).format("D MMM YYYY, h:mm A")
		: "",
)
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="lg">
			<div class="flex items-center gap-2 p-4 pb-0">
				<DrawerClose as-child>
					<Button size="sm" icon="lucide-chevrons-right" aria-label="Close" />
				</DrawerClose>
			</div>

			<!-- Reading a sent message -->
			<div v-if="viewing" class="flex flex-1 flex-col space-y-4 overflow-y-auto p-4">
				<DrawerTitle class="text-2xl font-semibold text-pretty text-ink-gray-9">
					{{ viewing.subject || "No subject" }}
				</DrawerTitle>
				<DrawerDescription class="text-base text-ink-gray-5">
					{{ viewing.sent_by }} · {{ viewedWhen }}
				</DrawerDescription>

				<div class="grid grid-cols-2 gap-x-5 gap-y-3">
					<div class="space-y-0.5">
						<p class="text-base text-ink-gray-5">Recipients</p>
						<p class="text-base text-ink-gray-8">{{ viewedFilters }}</p>
					</div>
					<div class="space-y-0.5">
						<p class="text-base text-ink-gray-5">Reached</p>
						<p class="text-base text-ink-gray-8">{{ viewing.recipient_count }} people</p>
					</div>
				</div>

				<!-- The same editor, read-only, rather than v-html: tiptap parses the stored
				     HTML into its own schema, so only what the composer can produce is rendered. -->
				<Editor :model-value="viewing.message" :extensions="richTextExtensions" :editable="false">
					<EditorContent
						class="prose prose-sm max-w-none text-base leading-[1.6] text-ink-gray-7"
					/>
				</Editor>
			</div>

			<!-- Composing -->
			<div v-else class="flex flex-1 flex-col space-y-4 overflow-y-auto p-4">
				<DrawerTitle class="text-2xl font-semibold text-ink-gray-9">New message</DrawerTitle>
				<DrawerDescription class="sr-only"
					>Choose who receives it, then write it.</DrawerDescription
				>

				<div class="grid grid-cols-2 gap-3">
					<Select
						v-model="draft.audience"
						label="Recipients"
						:options="audienceOptions"
						:disabled="!canWrite"
					/>
					<MultiSelect
						v-if="draft.audience === 'Guests'"
						v-model="draft.ticket_types"
						label="Ticket tiers"
						placeholder="All tiers"
						:options="tierOptions"
						:disabled="!canWrite"
					/>
					<MultiSelect
						v-else
						v-model="draft.statuses"
						label="Proposal status"
						placeholder="Any status"
						:options="statusOptions"
						:disabled="!canWrite"
					/>
				</div>
				<!-- The last count stays put and dims while the next one is fetched: swapping the
				     text for "Counting…" on every keystroke made the line jump. -->
				<p
					aria-live="polite"
					class="reach text-sm text-ink-gray-5"
					:class="count.loading && 'opacity-50'"
				>
					<template v-if="count.data">Reaches {{ count.data.count }} people</template>
					<template v-else>Counting…</template>
				</p>

				<FormControl
					v-model="draft.subject"
					type="text"
					label="Subject"
					placeholder="Defaults to the event title"
					:disabled="!canWrite"
				/>

				<div class="space-y-2">
					<label class="block text-xs text-ink-gray-5">Message</label>
					<Editor v-model="draft.message" :extensions="richTextExtensions" :editable="canWrite">
						<EditorFixedMenu
							:items="richTextToolbar"
							class="rounded-t-5 border border-b-0 border-outline-gray-2 px-2 py-1"
						/>
						<EditorContent
							class="prose prose-sm min-h-[12rem] max-w-none rounded-b-5 border border-outline-gray-2 px-3 py-2"
						/>
					</Editor>
				</div>

				<DateTimePicker
					v-if="scheduling"
					v-model="draft.scheduled_at"
					class="schedule-field"
					label="Send at"
					:min="minSchedule"
				/>
			</div>

			<template v-if="!viewing" #footer>
				<!-- Keyed on the mode, so a toggle morphs the pair through a short blur rather
				     than swapping two labels in one frame. -->
				<Transition name="mode" mode="out-in">
					<div :key="String(scheduling)" class="flex items-center gap-2">
						<Button
							variant="solid"
							:label="scheduling ? 'Schedule' : 'Send now'"
							:icon-left="scheduling ? 'lucide-mail-clock' : 'lucide-send'"
							:disabled="!canSend"
							:loading="sending"
							@click="send"
						/>
						<Button
							:label="scheduling ? 'Send now instead' : 'Schedule'"
							:icon-left="scheduling ? 'lucide-send' : 'lucide-mail-clock'"
							:disabled="!canWrite"
							@click="scheduling = !scheduling"
						/>
					</div>
				</Transition>
			</template>
		</DrawerContent>
	</Drawer>
</template>

<style scoped>
.reach,
.schedule-field,
.mode-enter-active,
.mode-leave-active {
	--ease-out: cubic-bezier(0.23, 1, 0.32, 1);
}

.reach {
	transition: opacity 150ms var(--ease-out);
}

/* Asked for, then shown: the field rises into the gap the footer's button opened. */
.schedule-field {
	transition:
		opacity 160ms var(--ease-out),
		transform 160ms var(--ease-out);
}

@starting-style {
	.schedule-field {
		opacity: 0;
		transform: translateY(4px);
	}
}

.mode-enter-active,
.mode-leave-active {
	transition:
		opacity 120ms var(--ease-out),
		filter 120ms var(--ease-out);
}

.mode-enter-from,
.mode-leave-to {
	opacity: 0.7;
	filter: blur(2px);
}

@media (prefers-reduced-motion: reduce) {
	.mode-enter-from,
	.mode-leave-to {
		filter: none;
	}

	@starting-style {
		.schedule-field {
			transform: none;
		}
	}
}
</style>
