<script setup lang="ts">
import { Button, Dialog, ErrorMessage, FormControl, toast } from "frappe-ui"
import { ref, watch } from "vue"

import { useUpdateSupportEmail } from "@/data/communications"
import type { FrappeError } from "@/types"

const props = defineProps<{ event: string; supportEmail: string | null; canEdit: boolean }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ changed: [] }>()

const email = ref("")
watch(isOpen, (open) => open && (email.value = props.supportEmail || ""))

const update = useUpdateSupportEmail()

async function save() {
	try {
		await update.submit({ event: props.event, support_email: email.value.trim() })
		toast.success("Reply-to address saved")
		emit("changed")
		isOpen.value = false
	} catch {
		// The error stays under the field.
	}
}

const message = (error: unknown) => (error as FrappeError | null)?.messages?.join("\n")
</script>

<template>
	<Dialog v-model="isOpen" size="sm" title="Email settings">
		<form class="space-y-4" @submit.prevent="save">
			<FormControl
				v-model="email"
				type="email"
				label="Support email"
				placeholder="hello@yourteam.com"
				description="Replies to every message this team sends go here. Leave it empty and replies go to whoever sent the message."
				:disabled="!canEdit"
			/>
			<ErrorMessage :message="message(update.error)" />
			<p v-if="!canEdit" class="text-sm text-ink-gray-5">
				Only a team owner or admin can change this.
			</p>
			<Button
				v-else
				type="submit"
				variant="solid"
				class="w-full"
				label="Save"
				:loading="update.loading"
			/>
		</form>
	</Dialog>
</template>
