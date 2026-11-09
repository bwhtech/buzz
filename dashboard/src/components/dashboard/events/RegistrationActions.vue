<script setup lang="ts">
import { call, toast } from "frappe-ui"
import { computed, ref } from "vue"

import GuestRegistrationDialog from "@/components/dashboard/events/GuestRegistrationDialog.vue"
import QuickActionsRail, {
	type QuickAction,
} from "@/components/dashboard/events/QuickActionsRail.vue"
import QuickActionTile from "@/components/dashboard/events/QuickActionTile.vue"
import RegistrationDialog from "@/components/dashboard/events/RegistrationDialog.vue"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{
	event: string
	closed: boolean
	canWrite: boolean
	registrationLink?: string | null
	registrationForm?: string | null
	allowGuestBooking: boolean
	guestVerificationMethod: string
	requiresApproval: boolean
	enableWaitlist: boolean
}>()
const emit = defineEmits<{ changed: [] }>()

const dialogOpen = ref(false)
const guestDialogOpen = ref(false)

const VERIFICATION_LABELS: Record<string, string> = {
	"Email OTP": "Email verification",
	"Phone OTP": "Phone verification",
}

const guestSubtitle = computed(() => {
	if (!props.allowGuestBooking) return "Disabled"
	const verification = VERIFICATION_LABELS[props.guestVerificationMethod]
	return verification ? `Enabled · ${verification}` : "Enabled"
})

async function toggleEventField(
	fieldname: "requires_approval" | "enable_waitlist",
	enabled: boolean,
) {
	try {
		await call("frappe.client.set_value", {
			doctype: "Buzz Event",
			name: props.event,
			fieldname,
			value: enabled ? 1 : 0,
		})
		emit("changed")
	} catch (error) {
		toast.error(serverErrorMessage(error) || "Could not save the setting. Try again.")
	}
}

const actions = computed<QuickAction[]>(() =>
	[
		props.registrationLink
			? { icon: "lucide-arrow-up-right", label: "Registration page", link: props.registrationLink }
			: null,
	].filter((action) => action !== null),
)
</script>

<template>
	<QuickActionsRail
		subject="Registration"
		open-icon="lucide-ticket"
		closed-icon="lucide-ticket-x"
		:closed="closed"
		:can-write="canWrite"
		:actions="actions"
		:form="canWrite ? registrationForm : null"
		@toggle="dialogOpen = true"
	>
		<QuickActionTile
			icon="lucide-hat-glasses"
			title="Guest registration"
			:subtitle="guestSubtitle"
			:tone="allowGuestBooking ? 'violet' : 'gray'"
			:disabled="!canWrite"
			@click="guestDialogOpen = true"
		/>
		<QuickActionTile
			icon="lucide-user-check"
			title="Approval"
			:subtitle="requiresApproval ? 'Required for all tickets' : 'Off'"
			:tone="requiresApproval ? 'amber' : 'gray'"
			:disabled="!canWrite"
			@click="toggleEventField('requires_approval', !requiresApproval)"
		/>
		<QuickActionTile
			icon="lucide-clock"
			title="Waitlist"
			:subtitle="enableWaitlist ? 'On for sold-out tickets' : 'Off'"
			:tone="enableWaitlist ? 'amber' : 'gray'"
			:disabled="!canWrite"
			@click="toggleEventField('enable_waitlist', !enableWaitlist)"
		/>
	</QuickActionsRail>

	<RegistrationDialog
		v-model="dialogOpen"
		:event="event"
		:closed="closed"
		@changed="emit('changed')"
	/>

	<GuestRegistrationDialog
		v-model="guestDialogOpen"
		:event="event"
		:enabled="allowGuestBooking"
		:method="guestVerificationMethod"
		@changed="emit('changed')"
	/>
</template>
