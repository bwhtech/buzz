<script setup lang="ts">
import { Button, Dialog, Textarea } from "frappe-ui"
import { ref, watch } from "vue"

import type { CommunityRequest } from "@/types"

const props = defineProps<{ request: CommunityRequest | null; loading: boolean }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ confirm: [reason: string] }>()

const reason = ref("")
watch(isOpen, (open) => open && (reason.value = ""))

const submitter = () =>
	props.request?.submitter_name || props.request?.submitted_by || __("The submitter")
</script>

<template>
	<Dialog v-model="isOpen" :title="__('Reject {0}?', [request?.event_title || ''])">
		<div class="space-y-3">
			<p class="text-base text-ink-gray-5">
				{{ __("It stays off your calendar. {0} gets an email with your reason.", [submitter()]) }}
			</p>
			<Textarea
				v-model="reason"
				:label="__('Reason')"
				:placeholder="__('Write your reason for rejection')"
				:rows="3"
				maxlength="500"
			/>
		</div>

		<template #actions="{ close }">
			<div class="flex gap-2">
				<Button
					theme="red"
					variant="solid"
					icon-left="lucide-x"
					:label="__('Reject')"
					:loading="loading"
					@click="emit('confirm', reason)"
				/>
				<Button variant="outline" :label="__('Cancel')" @click="close" />
			</div>
		</template>
	</Dialog>
</template>
