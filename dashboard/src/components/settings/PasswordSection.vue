<script setup lang="ts">
import { Button, createResource, toast } from "frappe-ui"

import { userResource } from "@/data/user"
import type { FrappeError } from "@/types"

const resetPassword = createResource({
	url: "frappe.core.doctype.user.user.reset_password",
	onSuccess() {
		toast.success(__("Password reset link sent to your email"))
	},
	onError(error: FrappeError) {
		toast.error(error.messages?.[0] || __("Could not send the password reset link"))
	},
})

function sendResetLink() {
	resetPassword.submit({ user: userResource.data?.email })
}
</script>

<template>
	<section class="flex flex-col gap-4">
		<span class="text-base-medium text-ink-gray-8">{{ __("Password") }}</span>

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
