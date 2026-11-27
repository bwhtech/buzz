<script setup lang="ts">
import { computed, ref } from "vue"

import GuestRegistrationDialog from "@/components/dashboard/events/GuestRegistrationDialog.vue"
import QuickActionsRail from "@/components/dashboard/events/QuickActionsRail.vue"
import QuickActionTile from "@/components/dashboard/events/QuickActionTile.vue"
import RegistrationDialog from "@/components/dashboard/events/RegistrationDialog.vue"

const props = defineProps<{
	event: string
	closed: boolean
	canWrite: boolean
	registrationForm?: string | null
	allowGuestBooking: boolean
	guestVerificationMethod: string
}>()
const emit = defineEmits<{ changed: [] }>()

const dialogOpen = ref(false)
const guestDialogOpen = ref(false)

const VERIFICATION_LABELS: Record<string, string> = {
	"Email OTP": "Email verification",
	"Phone OTP": "Phone verification",
}

const guestSubtitle = computed(() => {
	if (!props.allowGuestBooking) return "Login required"
	const verification = VERIFICATION_LABELS[props.guestVerificationMethod]
	return verification ? `No login needed · ${verification}` : "No login needed"
})
</script>

<template>
	<QuickActionsRail
		subject="Registration"
		open-icon="lucide-ticket"
		closed-icon="lucide-ticket-x"
		:closed="closed"
		:can-write="canWrite"
		:form="canWrite ? registrationForm : null"
		@toggle="dialogOpen = true"
	>
		<QuickActionTile
			icon="lucide-hat-glasses"
			title="Registration without login"
			:subtitle="guestSubtitle"
			:tone="allowGuestBooking ? 'violet' : 'gray'"
			:disabled="!canWrite"
			@click="guestDialogOpen = true"
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
