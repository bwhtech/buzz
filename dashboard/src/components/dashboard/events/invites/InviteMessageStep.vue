<script setup lang="ts">
// The note beside a live preview of the email; stacked on a phone.
import { Textarea } from "frappe-ui"

import InvitePreview from "./InvitePreview.vue"
import { MESSAGE_LIMIT } from "./invites"

const message = defineModel<string>({ required: true })
defineProps<{ event: string; eventTitle: string }>()
</script>

<template>
	<div
		class="grid min-h-0 flex-1 content-start overflow-y-auto md:content-stretch md:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] md:overflow-visible"
	>
		<section class="space-y-1.5 border-outline-gray-1 px-4 py-4 sm:px-5 md:border-r">
			<Textarea
				v-model="message"
				label="Add a note"
				:rows="6"
				:maxlength="MESSAGE_LIMIT"
				placeholder="Would love to have you there. Doors open at 9."
			/>
			<p class="text-right text-p-xs tabular-nums text-ink-gray-5">
				{{ message.length }} / {{ MESSAGE_LIMIT }}
			</p>
		</section>
		<section class="bg-surface-gray-1 px-4 py-5 sm:px-5 md:min-h-0 md:overflow-y-auto">
			<InvitePreview :event="event" :event-title="eventTitle" :message="message" />
		</section>
	</div>
</template>
