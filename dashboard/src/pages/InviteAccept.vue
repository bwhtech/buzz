<script setup lang="ts">
import { Badge, Button, dayjs, ErrorMessage, FormControl, Skeleton, useCall } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import type { GuestInvite } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ booking: string }>()

const route = useRoute()
const router = useRouter()
const token = String(route.query.token ?? "")
const firstName = ref("")
const lastName = ref("")

type InviteKey = { booking: string; token: string }

const invite = useCall<GuestInvite, InviteKey>({
	url: "/api/v2/method/buzz.api.booking.invites.get_invite",
	params: { booking: props.booking, token },
})
const accept = useCall<string, InviteKey & { first_name: string; last_name: string }>({
	url: "/api/v2/method/buzz.api.booking.invites.accept_invite",
	method: "POST",
	immediate: false,
})
const decline = useCall<null, InviteKey>({
	url: "/api/v2/method/buzz.api.booking.invites.decline_invite",
	method: "POST",
	immediate: false,
})

watch(
	() => invite.data,
	(data) => {
		firstName.value = data?.first_name ?? ""
		lastName.value = data?.last_name ?? ""
	},
)

const eventDateTime = computed(() => {
	const data = invite.data
	if (!data?.start_date) return ""
	const date = dayjs(data.start_date).format("ddd, D MMM YYYY")
	return data.start_time
		? `${date} · ${dayjs(`2000-01-01 ${data.start_time}`).format("h:mm A")}`
		: date
})
const error = computed(() => serverErrorMessage(accept.error ?? decline.error))

async function acceptInvite() {
	const path = await accept
		.submit({
			booking: props.booking,
			token,
			first_name: firstName.value,
			last_name: lastName.value,
		})
		.catch(() => null)
	if (path) router.replace(path)
}

async function declineInvite() {
	const declined = await decline
		.submit({ booking: props.booking, token })
		.then(() => true)
		.catch(() => false)
	if (declined) invite.reload()
}
</script>

<template>
	<div class="mx-auto flex max-w-md flex-col gap-6 px-4 py-12">
		<Skeleton v-if="invite.loading && !invite.data" class="h-72 w-full rounded-5" />

		<ErrorMessage v-else-if="invite.error" :message="serverErrorMessage(invite.error)" />

		<template v-else-if="invite.data">
			<header class="space-y-2">
				<p class="text-p-sm font-medium uppercase tracking-wide text-ink-gray-5">
					{{ __("You're invited") }}
				</p>
				<h1 class="text-3xl font-semibold leading-tight text-ink-gray-9">
					{{ invite.data.event_title }}
				</h1>
				<p class="text-p-base text-ink-gray-6">
					{{ [eventDateTime, invite.data.venue].filter(Boolean).join(" · ") }}
				</p>
				<Badge :label="invite.data.ticket_type" theme="gray" size="lg" />
			</header>

			<p v-if="invite.data.status === 'Confirmed'" class="text-p-base text-ink-gray-7">
				{{ __("You've accepted this invite. You're on the guest list.") }}
			</p>
			<p v-else-if="invite.data.status === 'Rejected'" class="text-p-base text-ink-gray-7">
				{{ __("You declined this invite. The organizer has been told.") }}
			</p>

			<form v-else class="space-y-4" @submit.prevent="acceptInvite">
				<div class="grid grid-cols-2 gap-3">
					<FormControl
						v-model="firstName"
						:label="__('First name')"
						required
						autocomplete="given-name"
					/>
					<FormControl v-model="lastName" :label="__('Last name')" autocomplete="family-name" />
				</div>
				<ErrorMessage :message="error" />
				<div class="flex flex-col gap-2">
					<Button
						type="submit"
						variant="solid"
						size="lg"
						:label="__('Accept invitation')"
						:loading="accept.loading"
						:disabled="!firstName.trim()"
					/>
					<Button
						variant="ghost"
						size="lg"
						:label="__('Can\'t make it')"
						:loading="decline.loading"
						@click="declineInvite"
					/>
				</div>
			</form>
		</template>
	</div>
</template>
