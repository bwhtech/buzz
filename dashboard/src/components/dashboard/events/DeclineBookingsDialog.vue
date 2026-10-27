<script setup lang="ts">
import { Button, Dialog, Textarea } from "frappe-ui"
import { ref, watch } from "vue"

defineProps<{ count: number; loading: boolean }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ confirm: [message: string] }>()

const message = ref("")
watch(isOpen, (open) => open && (message.value = ""))
</script>

<template>
	<Dialog
		v-model="isOpen"
		:title="count === 1 ? __('Decline this request?') : __('Decline {0} requests?', [count])"
	>
		<div class="space-y-3">
			<p class="text-base text-ink-gray-5">
				{{ __("They get an email, and can request to join again later.") }}
			</p>
			<Textarea
				v-model="message"
				:label="__('Message (optional)')"
				:placeholder="__('Add a note for the guest')"
				:rows="3"
				maxlength="500"
			/>
		</div>

		<template #actions="{ close }">
			<div class="flex gap-2">
				<Button
					theme="red"
					variant="solid"
					:label="__('Decline')"
					:loading="loading"
					@click="emit('confirm', message)"
				/>
				<Button variant="outline" :label="__('Cancel')" @click="close" />
			</div>
		</template>
	</Dialog>
</template>
