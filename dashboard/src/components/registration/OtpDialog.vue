<template>
	<Dialog
		v-model="open"
		:title="isPhone ? __('Verify your phone') : __('Verify your email')"
		size="sm"
		:dismissible="false"
	>
		<p class="mb-4 text-p-sm text-ink-gray-6">
			{{ __("Enter the 6-digit code sent to") }} <strong>{{ identifier }}</strong
			>.
			{{ __("The code expires in 10 minutes.") }}
		</p>
		<FormControl
			v-model="code"
			class="mb-3"
			maxlength="6"
			inputmode="numeric"
			autocomplete="one-time-code"
			:label="__('Verification code')"
			placeholder="123456"
			:error="error || undefined"
			@keyup.enter="emit('verify')"
			@input="emit('clear-error')"
		/>
		<Button
			variant="ghost"
			size="sm"
			:loading="resending"
			:disabled="resendCooldown > 0"
			@click="emit('resend')"
		>
			{{
				resendCooldown > 0
					? __("Didn't get the code? Resend in {0}s", [resendCooldown])
					: __("Resend code")
			}}
		</Button>
		<template #actions>
			<div class="flex justify-end gap-3">
				<Button variant="ghost" @click="emit('cancel')">{{ __("Cancel") }}</Button>
				<Button variant="solid" :loading="verifying" @click="emit('verify')">{{
					__("Verify & Book")
				}}</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Button, Dialog, FormControl } from "frappe-ui"

defineProps<{
	isPhone: boolean
	identifier: string
	error: string
	resendCooldown: number
	resending: boolean
	verifying: boolean
}>()
const emit = defineEmits<{ resend: []; verify: []; cancel: []; "clear-error": [] }>()

const open = defineModel<boolean>("open", { required: true })
const code = defineModel<string>("code", { required: true })
</script>
