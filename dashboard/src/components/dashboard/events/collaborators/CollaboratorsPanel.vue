<script setup lang="ts">
import { Badge, Button, Skeleton, dialog, toast } from "frappe-ui"
import { ref } from "vue"

import EditCollaboratorDialog from "@/components/dashboard/events/collaborators/EditCollaboratorDialog.vue"
import InviteCollaboratorsDialog from "@/components/dashboard/events/collaborators/InviteCollaboratorsDialog.vue"
import { useCollaborators, useRevokeCollaborators } from "@/data/collaborators"
import type { EventCollaborator } from "@/types"
import { describeLevels, levelsOf } from "@/utils/eventSections"

const props = defineProps<{ event: string }>()

const collaborators = useCollaborators(props.event)
const revokeCollaborators = useRevokeCollaborators()

const isInviting = ref(false)
const isEditing = ref(false)
const editing = ref<EventCollaborator | null>(null)

function edit(collaborator: EventCollaborator) {
	editing.value = collaborator
	isEditing.value = true
}

function confirmRevoke(collaborator: EventCollaborator) {
	dialog.confirm({
		title: __("Revoke access?"),
		message: __("{0} will no longer be able to open this event.", [collaborator.email]),
		theme: "red",
		confirmLabel: __("Revoke"),
		onConfirm: () => revoke(collaborator),
	})
}

async function revoke(collaborator: EventCollaborator) {
	await revokeCollaborators.submit({ event: props.event, emails: [collaborator.email] })
	if (revokeCollaborators.error) {
		toast.error(revokeCollaborators.error.message || __("Could not revoke access"))
		return
	}
	await collaborators.reload()
	toast.success(__("Access revoked"))
}
</script>

<template>
	<section class="space-y-3">
		<div class="flex items-center justify-between gap-3">
			<div>
				<h2 class="text-lg font-semibold text-ink-gray-9">{{ __("Collaborators") }}</h2>
				<p class="text-p-sm text-ink-gray-6">
					{{ __("People who can open only this event, section by section.") }}
				</p>
			</div>
			<Button variant="solid" :label="__('Invite')" @click="isInviting = true" />
		</div>

		<div class="overflow-hidden rounded-6 border border-outline-gray-2">
			<div v-if="!collaborators.data" class="p-4">
				<Skeleton class="h-11 w-full rounded-4" />
			</div>

			<p v-else-if="!collaborators.data.length" class="p-4 text-base text-ink-gray-6">
				{{ __("No collaborators yet.") }}
			</p>

			<div v-else class="divide-y divide-outline-gray-1">
				<div
					v-for="collaborator in collaborators.data"
					:key="collaborator.name"
					class="flex flex-wrap items-center justify-between gap-3 p-4"
				>
					<div class="min-w-0 space-y-1">
						<div class="flex items-center gap-2">
							<span class="truncate font-medium text-base text-ink-gray-8">{{
								collaborator.email
							}}</span>
							<Badge
								:label="__(collaborator.status)"
								:theme="collaborator.status === 'Accepted' ? 'green' : 'amber'"
							/>
						</div>
						<p class="text-p-sm text-ink-gray-6">{{ describeLevels(levelsOf(collaborator)) }}</p>
					</div>

					<div class="flex gap-2">
						<Button variant="subtle" :label="__('Edit access')" @click="edit(collaborator)" />
						<Button
							variant="subtle"
							theme="red"
							:label="__('Revoke')"
							:loading="revokeCollaborators.loading"
							@click="confirmRevoke(collaborator)"
						/>
					</div>
				</div>
			</div>
		</div>

		<InviteCollaboratorsDialog
			v-model="isInviting"
			:event="event"
			@success="collaborators.reload()"
		/>
		<EditCollaboratorDialog
			v-model="isEditing"
			:event="event"
			:collaborator="editing"
			@success="collaborators.reload()"
		/>
	</section>
</template>
