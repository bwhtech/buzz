<script setup lang="ts">
import { Button, useCall } from "frappe-ui"

import { serverErrorMessage } from "@/utils/serverError"

const start = useCall<{ redirect_to: string }>({
	url: "/api/v2/method/buzz.api.playground.start",
	method: "POST",
	immediate: false,
	onSuccess: (data) => window.location.assign(data.redirect_to),
})
</script>

<template>
	<div class="flex flex-col items-start gap-6 py-16">
		<div class="flex flex-col gap-3">
			<h1 class="text-3xl-semibold text-ink-gray-9">{{ __("Try Buzz, no signup") }}</h1>
			<p class="max-w-xl text-lg text-ink-gray-7">
				{{
					__(
						"Get your own sandbox with a conference, a meetup and a past event. Create ticket tiers, book tickets, check guests in, and read every email Buzz sends. It resets after 24 hours.",
					)
				}}
			</p>
		</div>
		<Button
			v-if="!start.error"
			variant="solid"
			size="lg"
			:loading="start.loading"
			@click="start.submit()"
		>
			{{ __("Start exploring") }}
		</Button>
		<p v-else class="text-base text-ink-red-4">{{ serverErrorMessage(start.error) }}</p>
	</div>
</template>
