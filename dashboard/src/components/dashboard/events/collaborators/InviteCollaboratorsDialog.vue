<script setup lang="ts">
import { Button, Dialog, ErrorMessage, FormControl, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"

import CollaboratorAccessFields from "@/components/dashboard/events/collaborators/CollaboratorAccessFields.vue"
import { useInviteCollaborators } from "@/data/collaborators"
import { emptySectionLevels } from "@/utils/eventSections"
import { serverErrorMessage } from "@/utils/serverError"

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const props = defineProps<{ event: string }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ success: [] }>()

const inviteCollaborators = useInviteCollaborators()
const emails = ref("")
const levels = ref(emptySectionLevels())
const errorMessage = ref("")

const addresses = computed(() =>
	emails.value
		.split(/[\s,;]+/)
		.map((address) => address.trim())
		.filter(Boolean),
)
const hasInvalidAddress = computed(() =>
	addresses.value.some((address) => !EMAIL_PATTERN.test(address)),
)

watch(isOpen, (open) => {
	if (!open) return
	emails.value = ""
	levels.value = emptySectionLevels()
	errorMessage.value = ""
})

async function submit() {
	if (!addresses.value.length) return
	if (hasInvalidAddress.value) {
		errorMessage.value = __("Check the email addresses.")
		return
	}

	await inviteCollaborators.submit({
		event: props.event,
		invites: addresses.value.map((email) => ({ email, ...levels.value })),
	})
	errorMessage.value = serverErrorMessage(inviteCollaborators.error)
	if (inviteCollaborators.error) return

	toast.success(__("Invitation sent"))
	emit("success")
	isOpen.value = false
}
</script>

<template>
	<Dialog v-model="isOpen" :title="__('Invite collaborators')" size="xl">
		<div class="space-y-4">
			<p class="text-base text-ink-gray-5">
				{{
					__(
						"Collaborators get an email invitation and see only this event, and only the sections you choose.",
					)
				}}
			</p>

			<FormControl
				v-model="emails"
				type="text"
				:label="__('Email')"
				placeholder="person@example.com"
				@keydown.enter.prevent="submit"
			/>

			<CollaboratorAccessFields v-model="levels" />

			<ErrorMessage :message="errorMessage" />
		</div>

		<template #actions="{ close }">
			<div class="flex gap-2">
				<Button
					variant="solid"
					:label="__('Send invite')"
					:loading="inviteCollaborators.loading"
					:disabled="!addresses.length"
					@click="submit"
				/>
				<Button variant="outline" :label="__('Cancel')" @click="close" />
			</div>
		</template>
	</Dialog>
</template>
