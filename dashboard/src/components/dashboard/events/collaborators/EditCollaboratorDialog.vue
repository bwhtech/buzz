<script setup lang="ts">
import { Button, Dialog, ErrorMessage, toast } from "frappe-ui"
import { ref, watch } from "vue"

import CollaboratorAccessFields from "@/components/dashboard/events/collaborators/CollaboratorAccessFields.vue"
import { useUpdateCollaboratorAccess } from "@/data/collaborators"
import type { EventCollaborator } from "@/types"
import { emptySectionLevels, levelsOf } from "@/utils/eventSections"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ event: string; collaborator: EventCollaborator | null }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ success: [] }>()

const updateAccess = useUpdateCollaboratorAccess()
const levels = ref(emptySectionLevels())
const errorMessage = ref("")

watch(isOpen, (open) => {
	if (!open || !props.collaborator) return
	levels.value = levelsOf(props.collaborator)
	errorMessage.value = ""
})

async function submit() {
	if (!props.collaborator) return
	await updateAccess.submit({
		event: props.event,
		email: props.collaborator.email,
		sections: levels.value,
	})
	errorMessage.value = serverErrorMessage(updateAccess.error)
	if (updateAccess.error) return

	toast.success(__("Access updated"))
	emit("success")
	isOpen.value = false
}
</script>

<template>
	<Dialog v-model="isOpen" :title="__('Edit access')" size="xl">
		<div class="space-y-4">
			<p class="text-base text-ink-gray-5">{{ collaborator?.email }}</p>
			<CollaboratorAccessFields v-model="levels" />
			<ErrorMessage :message="errorMessage" />
		</div>

		<template #actions="{ close }">
			<div class="flex gap-2">
				<Button
					variant="solid"
					:label="__('Save')"
					:loading="updateAccess.loading"
					@click="submit"
				/>
				<Button variant="outline" :label="__('Cancel')" @click="close" />
			</div>
		</template>
	</Dialog>
</template>
