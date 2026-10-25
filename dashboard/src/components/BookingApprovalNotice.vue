<template>
	<div class="rounded-6 border p-4" :class="copy.classes">
		<div class="flex items-start gap-3">
			<component :is="copy.icon" class="mt-0.5 size-5 shrink-0" />
			<div class="flex flex-1 flex-col gap-1">
				<h3 class="font-semibold">{{ copy.title }}</h3>
				<p class="text-sm">{{ copy.message }}</p>
				<p v-if="state === 'declined' && rejectionReason" class="text-sm font-medium">
					{{ rejectionReason }}
				</p>
			</div>
			<Button
				v-if="state === 'pending'"
				variant="outline"
				theme="red"
				:label="__('Withdraw request')"
				:loading="withdraw.loading"
				@click="withdrawRequest"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, toast, useCall } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"
import LucideBan from "~icons/lucide/ban"
import LucideClock from "~icons/lucide/clock"
import LucideHourglass from "~icons/lucide/hourglass"
import LucideXCircle from "~icons/lucide/x-circle"

import type { ApprovalState } from "@/utils/bookingApproval"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{
	bookingId: string
	state: ApprovalState
	rejectionReason?: string | null
}>()
const emit = defineEmits<{ changed: [] }>()

const route = useRoute()

const withdraw = useCall<null, { booking: string; token?: string }>({
	url: "/api/v2/method/buzz.api.booking.approvals.withdraw_booking",
	method: "POST",
	immediate: false,
})

const COPY = {
	pending: {
		icon: LucideClock,
		classes: "border-yellow-200 bg-yellow-50 text-yellow-800",
		title: __("Pending approval"),
		message: __(
			"The organizer is reviewing your request. We'll email you once they decide. No ticket has been issued yet.",
		),
	},
	declined: {
		icon: LucideXCircle,
		classes: "border-red-200 bg-red-50 text-red-800",
		title: __("Request declined"),
		message: __("The organizer wasn't able to confirm your spot this time."),
	},
	withdrawn: {
		icon: LucideBan,
		classes: "border-outline-gray-2 bg-surface-gray-1 text-ink-gray-7",
		title: __("Request withdrawn"),
		message: __("You withdrew this request."),
	},
	expired: {
		icon: LucideHourglass,
		classes: "border-outline-gray-2 bg-surface-gray-1 text-ink-gray-7",
		title: __("Request expired"),
		message: __("The organizer didn't respond before the event ended."),
	},
}

const copy = computed(() => COPY[props.state])

async function withdrawRequest() {
	const token = route.query.token ? String(route.query.token) : undefined
	await withdraw.submit({ booking: props.bookingId, token })
	if (withdraw.error) return toast.error(serverErrorMessage(withdraw.error))
	toast.success(__("Request withdrawn"))
	emit("changed")
}
</script>
