<template>
	<Alert
		:theme="notice.theme"
		:title="__(notice.title)"
		:description="__(notice.message)"
		:primary-action="payAction"
	/>
</template>

<script setup lang="ts">
import { Alert, toast, useCall } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import type { RequestNotice } from "@/utils/registrationRequest"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ bookingId: string; notice: RequestNotice }>()

const route = useRoute()
const redirecting = ref(false)

const paymentLink = useCall<{ payment_link: string }, { booking: string; token?: string }>({
	url: "/api/v2/method/buzz.api.booking.requests.get_request_payment_link",
	method: "POST",
	immediate: false,
})

const payAction = computed(() =>
	props.notice.canPay
		? { label: __("Pay now"), loading: paymentLink.loading || redirecting.value, onClick: payNow }
		: undefined,
)

async function payNow() {
	const token = route.query.token ? String(route.query.token) : undefined
	try {
		const data = await paymentLink.submit({ booking: props.bookingId, token })
		if (!data) return
		redirecting.value = true
		window.location.href = data.payment_link
	} catch (error) {
		toast.error(serverErrorMessage(error) || __("Could not start payment"))
	}
}
</script>
