<script setup lang="ts">
import { Button, toast, useCall } from "frappe-ui"

import { userResource } from "@/data/user"
import { serverErrorMessage } from "@/utils/serverError"

const resetPassword = useCall<unknown, { user?: string }>({
	url: "/api/v2/method/frappe.core.doctype.user.user.reset_password",
	method: "POST",
	immediate: false,
	onSuccess() {
		toast.success(__("Password reset link sent to your email"))
	},
	onError(error) {
		toast.error(serverErrorMessage(error) || __("Could not send the password reset link"))
	},
})

function sendResetLink() {
	resetPassword.submit({ user: userResource.data?.email })
}
</script>

<template>
	<section class="flex flex-col gap-4">
		<span class="text-lg-semibold text-ink-gray-8">{{ __("Account") }}</span>

		<div class="flex items-center justify-between gap-4">
			<div class="flex flex-col gap-1">
				<span class="text-base-medium text-ink-gray-8">{{ __("Reset Password") }}</span>
				<span class="text-p-sm text-ink-gray-6">
					{{ __("We'll email you a link to set a new password.") }}
				</span>
			</div>

			<Button variant="subtle" :loading="resetPassword.loading" @click="sendResetLink">
				{{ __("Reset Password") }}
			</Button>
		</div>
	</section>
</template>
