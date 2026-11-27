<template>
	<Alert
		:theme="notice.theme"
		:title="__(notice.title)"
		:description="__(notice.message)"
		:primary-action="payAction ?? viewAction"
		:secondary-action="payAction && viewAction"
	/>
</template>

<script setup lang="ts">
import { Alert, toast, useCall } from "frappe-ui"
import { computed, onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import type { RequestNotice } from "@/utils/registrationRequest"
import { serverErrorMessage } from "@/utils/serverError"

// `showLink` adds View request, for pages other than the request's own.
const props = defineProps<{ bookingId: string; notice: RequestNotice; showLink?: boolean }>()

const route = useRoute()
const router = useRouter()
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

const viewAction = computed(() =>
	props.showLink
		? {
				label: __("View request"),
				onClick: viewRequest,
			}
		: undefined,
)

async function viewRequest() {
	await router.push({ name: "booking-success", params: { bookingId: props.bookingId } })
}

// The approval email links here with ?pay=1, so its Pay now goes straight to the gateway.
onMounted(() => {
	if (route.query.pay !== "1") return
	const query = { ...route.query }
	delete query.pay
	router.replace({ query })
	if (props.notice.canPay) payNow()
})

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
