<script setup lang="ts">
import { Avatar, Button, FormControl, TextInput, Textarea } from "frappe-ui"
import { ref } from "vue"

import InvitePreview from "./InvitePreview.vue"
import { displayName, type Invitee, MESSAGE_LIMIT, type TierOption } from "./invites"

const selected = defineModel<Invitee[]>({ required: true })
const message = defineModel<string>("message", { required: true })
const props = defineProps<{
	tiers: TierOption[]
	defaultTier: string
	eventTitle: string
	host: string
	// Add directly books a ticket now, so every row needs a name the organizer typed.
	askNames: boolean
}>()
// Removal goes through the selection, so undo keeps its history straight.
const emit = defineEmits<{ remove: [invitee: Invitee] }>()

const tierForAll = ref(props.defaultTier)
// Rows that arrived without a name keep their name field while the organizer types into it.
const nameless = new Set(
	selected.value.filter((invitee) => !invitee.first_name).map((row) => row.id),
)

function applyTierToAll(tier: string) {
	tierForAll.value = tier
	for (const invitee of selected.value) invitee.ticket_type = tier
}
</script>

<template>
	<div class="grid min-h-0 flex-1 md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
		<section class="flex min-h-0 flex-col border-outline-gray-1 md:border-r">
			<div class="flex items-center justify-between gap-2 px-5 pb-2 pt-4">
				<h4 class="text-base font-medium text-ink-gray-9">Ticket</h4>
				<!-- FormControl hands `class` to its input, so a wrapper sets the width. -->
				<div class="w-44">
					<FormControl
						type="select"
						size="sm"
						aria-label="Ticket for everyone"
						:model-value="tierForAll"
						:options="tiers"
						@update:model-value="applyTierToAll"
					/>
				</div>
			</div>
			<ul class="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
				<li
					v-for="invitee in selected"
					:key="invitee.id"
					class="group flex items-center gap-3 rounded-4 px-2 py-1.5 hover:bg-surface-gray-2"
				>
					<Avatar :label="displayName(invitee)" size="md" />
					<div class="min-w-0 flex-1">
						<span class="block truncate text-p-sm text-ink-gray-9">{{ displayName(invitee) }}</span>
						<div v-if="askNames && nameless.has(invitee.id)" class="mt-1">
							<TextInput
								v-model="invitee.first_name"
								size="sm"
								placeholder="First name"
								:aria-label="`First name for ${invitee.email}`"
							/>
						</div>
						<span v-else-if="invitee.first_name" class="block truncate text-p-xs text-ink-gray-5">
							{{ invitee.email }}
						</span>
					</div>
					<div class="w-36 shrink-0">
						<FormControl
							v-model="invitee.ticket_type"
							type="select"
							size="sm"
							:aria-label="`Ticket for ${displayName(invitee)}`"
							:options="tiers"
						/>
					</div>
					<Button
						variant="ghost"
						size="sm"
						icon="lucide-x"
						class="shrink-0 opacity-0 group-hover:opacity-100 focus-visible:opacity-100"
						:label="`Remove ${displayName(invitee)}`"
						@click="emit('remove', invitee)"
					/>
				</li>
			</ul>
		</section>

		<section class="min-h-0 space-y-3 overflow-y-auto px-5 py-4">
			<div class="space-y-1.5">
				<Textarea v-model="message" label="Custom message" :rows="3" :maxlength="MESSAGE_LIMIT" />
				<p class="text-right text-p-xs tabular-nums text-ink-gray-5">
					{{ message.length }} / {{ MESSAGE_LIMIT }}
				</p>
			</div>
			<InvitePreview :event-title="eventTitle" :host="host" :message="message" />
		</section>
	</div>
</template>
