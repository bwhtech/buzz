<script setup lang="ts">
import { Button, Dialog, ErrorMessage, toast, useDoc } from "frappe-ui"
import { computed, watch } from "vue"

import type { FrappeError } from "@/types"

const props = defineProps<{ form: string; closed: boolean }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ changed: [] }>()

// Only the method is used; the form itself is never fetched.
const form = useDoc<{ name: string }, { setClosed: (params: { closed: boolean }) => boolean }>({
	doctype: "Sponsor Enquiry Form",
	name: () => props.form,
	immediate: false,
	methods: { setClosed: "set_closed" },
})
const setClosed = form.setClosed

const errorMessage = computed(() => (setClosed.error as FrappeError | null)?.messages?.join("\n"))

watch(isOpen, (open) => open && setClosed.reset())

// The server owns the state, so the toast reports what came back rather than what was asked for.
async function submit() {
	const closing = !props.closed
	await setClosed.submit({ closed: closing })
	if (setClosed.error) return

	if (setClosed.data === closing) {
		toast.success(closing ? "Enquiries closed" : "Enquiries open")
	} else {
		toast.warning("Enquiries stay closed.")
	}
	emit("changed")
	isOpen.value = false
}
</script>

<template>
	<Dialog v-model="isOpen" size="sm" :title="closed ? 'Open enquiries' : 'Close enquiries'">
		<div class="space-y-4">
			<p class="text-p-base text-ink-gray-6">
				{{
					closed
						? "The sponsorship form accepts new enquiries again."
						: "New sponsorship enquiries stop immediately. Enquiries already in are unaffected."
				}}
			</p>

			<ErrorMessage :message="errorMessage" />

			<Button
				variant="solid"
				class="w-full"
				:theme="closed ? 'gray' : 'red'"
				:label="closed ? 'Open enquiries' : 'Close enquiries'"
				:loading="setClosed.loading"
				@click="submit"
			/>
		</div>
	</Dialog>
</template>
