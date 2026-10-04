<script setup lang="ts">
import {
	Alert,
	Dialog,
	type DialogAction,
	Radio,
	RadioGroup,
	Skeleton,
	Switch,
	call,
	toast,
} from "frappe-ui"
import { computed, ref, watch } from "vue"

import { useVerificationMethods } from "@/data/events"
import type { VerificationMethods } from "@/types"

const props = defineProps<{ event: string; enabled: boolean; method: string }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ changed: [] }>()

const enabled = ref(props.enabled)
// The doctype's own option strings, so nothing has to be mapped on the way out.
const method = ref(props.method)

// Site configuration, so it is read on every open rather than once: an admin can set up
// email while the organiser has the page sitting there.
const methods = useVerificationMethods()

watch(isOpen, (open) => {
	if (!open) return
	enabled.value = props.enabled
	method.value = props.method
	methods.submit()
})

function canDeliver(value: string, site: VerificationMethods) {
	if (value === "Email OTP") return site.email
	if (value === "Phone OTP") return site.phone
	return true
}

// A method the site cannot deliver is not a method. Nothing server-side refuses Phone
// OTP without a gateway, so turning the switch on would otherwise save a config no guest
// can complete.
watch(
	() => methods.data,
	(site) => {
		if (site && !canDeliver(method.value, site)) method.value = "None"
	},
)

const unavailable = computed(() => {
	if (!methods.data) return null
	const missing = [methods.data.email ? null : "email", methods.data.phone ? null : "SMS"].filter(
		(channel) => channel !== null,
	)

	if (!missing.length) return null
	if (missing.length === 2) {
		return {
			title: "Verification is not available",
			description:
				"Neither email nor SMS is configured on this site. Ask your administrator to set one up.",
		}
	}
	return missing[0] === "email"
		? {
				title: "Email verification is not available",
				description:
					"No outgoing email account is configured on this site. Ask your administrator to set one up.",
			}
		: {
				title: "Phone verification is not available",
				description:
					"No SMS gateway is configured for guests on this site. Ask your administrator to set one up.",
			}
})

async function save(close: () => void) {
	try {
		await call("frappe.client.set_value", {
			doctype: "Buzz Event",
			name: props.event,
			fieldname: {
				allow_guest_booking: enabled.value ? 1 : 0,
				guest_verification_method: method.value,
			},
		})
		toast.success("Guest registration settings saved")
		emit("changed")
		close()
	} catch (error) {
		// The event refuses Email OTP without an outgoing email account, so the server's
		// own reason is more useful than a generic failure.
		toast.error((error as Error)?.message || "Could not save the settings. Try again.")
	}
}

// The dialog runs its own loading state around an async onClick, so saving needs no ref.
// Save waits for the site's answer: until it lands, the options on screen are either
// absent or a previous open's, and neither is what this save would be written against.
const actions = computed<DialogAction[]>(() => [
	{ label: "Cancel" },
	{
		label: "Save",
		variant: "solid",
		disabled: !methods.data || methods.loading,
		onClick: ({ close }) => save(close),
	},
])
</script>

<template>
	<Dialog v-model="isOpen" title="Guest registration" :actions="actions">
		<div class="space-y-4">
			<Switch
				v-model="enabled"
				padded
				label="Accept guest registrations"
				description="Guests can register themselves from the registration page."
			/>

			<!-- Skeletons rather than enabled options: an option drawn before the site's
				 configuration is known is an option that may be about to disable itself. -->
			<div v-if="!methods.data" class="space-y-2">
				<Skeleton class="h-4 w-32 rounded-4" />
				<Skeleton v-for="row in 3" :key="row" class="h-14 w-full rounded-4" />
			</div>

			<template v-else>
				<RadioGroup v-model="method" padded label="Verification method" :disabled="!enabled">
					<Radio
						value="None"
						label="None"
						description="Guests are registered as soon as they submit the form."
					/>
					<Radio
						value="Email OTP"
						label="Email"
						description="A 6-digit code is sent by email before the spot is held."
						:disabled="!methods.data.email"
					/>
					<Radio
						value="Phone OTP"
						label="Phone OTP"
						description="A 6-digit code is sent over SMS before the spot is held."
						:disabled="!methods.data.phone"
					/>
				</RadioGroup>

				<Alert
					v-if="unavailable"
					theme="amber"
					:title="unavailable.title"
					:description="unavailable.description"
				/>
			</template>
		</div>
	</Dialog>
</template>
