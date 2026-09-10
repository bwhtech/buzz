<script setup lang="ts">
import { useLocalStorage } from "@vueuse/core"
import { ErrorMessage, Skeleton, dayjsLocal, toast } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import CommunicationActions from "@/components/dashboard/communications/CommunicationActions.vue"
import CommunicationComposer from "@/components/dashboard/communications/CommunicationComposer.vue"
import CommunicationDrawer from "@/components/dashboard/communications/CommunicationDrawer.vue"
import CommunicationHistory from "@/components/dashboard/communications/CommunicationHistory.vue"
import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import { useEventCommunications, useSendCommunication } from "@/data/communications"
import { session } from "@/data/session"
import PageWithSidebar from "@/layouts/PageWithSidebar.vue"
import type { CommunicationDraft, CommunicationItem, FrappeError } from "@/types"

const route = useRoute()
const eventId = route.params.eventId as string

const page = useEventCommunications(eventId)

const emptyDraft = (): CommunicationDraft => ({
	audience: "Guests",
	ticket_types: [],
	statuses: [],
	subject: "",
	message: "",
	scheduled_at: "",
})
// One draft for the inline box and the drawer, so Advanced continues what was typed.
// Kept in localStorage per event: a tab switch or reload must not eat a half-written message.
const draft = useLocalStorage<CommunicationDraft>(
	// Keyed by user too: a shared browser must not hand one account's draft to the next.
	`buzz:communication-draft:${session.user}:${eventId}`,
	emptyDraft(),
	{
		mergeDefaults: true,
	},
)

const drawerOpen = ref(false)
const viewing = ref<CommunicationItem | null>(null)

function openAdvanced() {
	viewing.value = null
	drawerOpen.value = true
}
function openSent(row: CommunicationItem) {
	viewing.value = row
	drawerOpen.value = true
}

const sender = useSendCommunication()
const message = (error: unknown) => (error as FrappeError | null)?.messages?.join("\n")

async function send() {
	try {
		const sent = await sender.submit({
			event: eventId,
			audience: draft.value.audience,
			ticket_types: draft.value.ticket_types.join(","),
			statuses: draft.value.statuses.join(","),
			subject: draft.value.subject,
			message: draft.value.message,
			scheduled_at: draft.value.scheduled_at || null,
		})
		draft.value = emptyDraft()
		drawerOpen.value = false
		page.reload()
		if (sent) announce(sent)
	} catch (error) {
		toast.error(message(error) || "Could not send the message. Try again.")
	}
}

// Nothing has left yet: the queue sends on the scheduler's next pass, so the toast says
// "queued" and offers the row rather than claiming delivery.
function announce(sent: CommunicationItem) {
	const noun = sent.audience === "Guests" ? "guest" : "speaker"
	const who = `${sent.recipient_count} ${noun}${sent.recipient_count === 1 ? "" : "s"}`
	const scheduled = sent.scheduled_at ? dayjsLocal(sent.scheduled_at) : null
	toast.success(
		scheduled ? `Scheduled for ${scheduled.format("D MMM, h:mm A")}` : `Queued for ${who}`,
		{
			description: scheduled
				? `${who} will get it then.`
				: "Emails go out over the next few minutes.",
			action: { label: "View", onClick: () => openSent(sent) },
		},
	)
}

const canWrite = computed(() => !!page.data?.can_write)
</script>

<template>
	<EventPageHeader :title="page.data?.title" section="Announcements" />

	<PageWithSidebar>
		<EventArchivedAlert :event="eventId" />

		<section class="space-y-3">
			<h1 class="text-xl font-semibold text-ink-gray-9">Send an Announcement</h1>
			<Skeleton v-if="page.loading && !page.data" class="h-40 w-full rounded-8" />
			<CommunicationComposer
				v-else
				v-model="draft"
				:can-write="canWrite"
				:sending="sender.loading"
				@advanced="openAdvanced"
				@send="send"
			/>
			<ErrorMessage :message="message(page.error)" />
		</section>

		<section class="space-y-3">
			<h2 class="text-xl font-semibold text-ink-gray-9">Sent</h2>
			<div v-if="page.loading && !page.data" class="space-y-3">
				<Skeleton v-for="row in 3" :key="row" class="h-14 w-full rounded-8" />
			</div>
			<CommunicationHistory
				v-else
				:communications="page.data?.communications || []"
				@open="openSent"
			/>
		</section>

		<template #sidebar>
			<CommunicationActions
				v-if="page.data"
				:event="eventId"
				:support-email="page.data.support_email"
				:can-edit="page.data.can_edit_settings"
				@changed="page.reload()"
			/>
		</template>
	</PageWithSidebar>

	<CommunicationDrawer
		v-model:open="drawerOpen"
		v-model:draft="draft"
		:event="eventId"
		:options="page.data"
		:viewing="viewing"
		:can-write="canWrite"
		:sending="sender.loading"
		@send="send"
	/>
</template>
