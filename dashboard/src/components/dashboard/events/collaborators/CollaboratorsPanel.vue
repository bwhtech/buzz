<script setup lang="ts">
import { Avatar, Badge, Button, Dropdown, Icon, Skeleton, dialog, toast } from "frappe-ui"
import { computed, ref } from "vue"

import EmptyState from "@/components/common/EmptyState.vue"
import CollaboratorDrawer from "@/components/dashboard/events/collaborators/CollaboratorDrawer.vue"
import {
	useCollaborators,
	useInviteCollaborators,
	useRevokeCollaborators,
} from "@/data/collaborators"
import type { EventCollaborator } from "@/types"
import { grantedSections, levelsOf } from "@/utils/eventSections"
import { invitationActions } from "@/utils/invitationActions"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ event: string }>()

const collaborators = useCollaborators(props.event)
const resendInvite = useInviteCollaborators()
const revokeCollaborators = useRevokeCollaborators()

const isDrawerOpen = ref(false)
const editing = ref<EventCollaborator | null>(null)

const taken = computed(() => (collaborators.data ?? []).map((collaborator) => collaborator.email))

function openDrawer(collaborator: EventCollaborator | null) {
	editing.value = collaborator
	isDrawerOpen.value = true
}

function actionsFor(collaborator: EventCollaborator) {
	const edit = {
		label: __("Edit access"),
		icon: "lucide-sliders-horizontal",
		onClick: () => openDrawer(collaborator),
	}
	if (collaborator.status === "Pending")
		return [
			edit,
			...invitationActions({
				resend: () => resend(collaborator),
				retract: () => confirmRevoke(collaborator),
			}),
		]
	return [
		edit,
		{
			label: __("Revoke access"),
			icon: "lucide-user-minus",
			theme: "red" as const,
			onClick: () => confirmRevoke(collaborator),
		},
	]
}

// Inviting a pending address again issues a fresh link with the access it already has.
async function resend(collaborator: EventCollaborator) {
	if (resendInvite.loading) return
	await resendInvite
		.submit({
			event: props.event,
			invites: [{ email: collaborator.email, ...levelsOf(collaborator) }],
		})
		.catch(() => null)
	if (resendInvite.error) return toast.error(serverErrorMessage(resendInvite.error))
	toast.success(__("Invitation resent to {0}.", [collaborator.email]))
}

function confirmRevoke(collaborator: EventCollaborator) {
	const isPending = collaborator.status === "Pending"
	dialog.confirm({
		title: isPending ? __("Retract invitation") : __("Revoke access"),
		message: isPending
			? __("The invitation link sent to {0} will stop working.", [collaborator.email])
			: __("{0} will no longer be able to open this event.", [collaborator.email]),
		theme: "red",
		confirmLabel: isPending ? __("Retract") : __("Revoke"),
		onConfirm: async () => {
			await revokeCollaborators
				.submit({ event: props.event, emails: [collaborator.email] })
				.catch(() => null)
			if (revokeCollaborators.error) throw revokeCollaborators.error
			isDrawerOpen.value = false
			await collaborators.reload()
			toast.success(isPending ? __("Invitation retracted") : __("Access revoked"))
		},
	})
}
</script>

<template>
	<section class="flex flex-col gap-3">
		<div class="flex flex-wrap items-end justify-between gap-x-4 gap-y-3">
			<div class="flex min-w-0 flex-[1_1_16rem] flex-col gap-1">
				<h2 class="text-lg font-semibold text-ink-gray-9">{{ __("Collaborators") }}</h2>
				<p class="text-p-sm text-pretty text-ink-gray-5">
					{{ __("People outside your team who can open this event, section by section") }}
				</p>
			</div>
			<div class="flex shrink-0 items-center gap-2.5">
				<div v-if="collaborators.data?.length" class="flex -space-x-1.5" aria-hidden="true">
					<Avatar
						v-for="collaborator in collaborators.data.slice(0, 3)"
						:key="collaborator.name"
						:label="collaborator.email"
						size="sm"
					/>
				</div>
				<Button
					variant="solid"
					icon-left="lucide-plus"
					:label="__('Invite')"
					@click="openDrawer(null)"
				/>
			</div>
		</div>

		<div class="rounded-6 border border-outline-gray-2 p-1">
			<Skeleton v-if="!collaborators.data" class="h-14 w-full rounded-5" />

			<EmptyState
				v-else-if="!collaborators.data.length"
				icon="lucide-users"
				:title="__('No collaborators yet')"
				:description="
					__(
						'Bring in a co-host, check-in crew or sponsor lead. They see only the sections you pick.',
					)
				"
			>
				<Button
					variant="subtle"
					icon-left="lucide-plus"
					:label="__('Invite collaborator')"
					@click="openDrawer(null)"
				/>
			</EmptyState>

			<TransitionGroup v-else tag="ul" name="collaborator" class="relative">
				<li
					v-for="collaborator in collaborators.data"
					:key="collaborator.name"
					class="flex items-center gap-2 rounded-5 pr-2 transition-colors duration-150 ease-out hover:bg-surface-gray-1"
				>
					<button
						type="button"
						class="flex min-w-0 flex-1 items-center gap-3 rounded-5 py-2.5 pl-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
						:aria-label="__('Edit access for {0}', [collaborator.email])"
						@click="openDrawer(collaborator)"
					>
						<Avatar :label="collaborator.email" size="xl" />
						<div class="flex min-w-0 flex-1 flex-col gap-1">
							<div class="flex min-w-0 items-center gap-2">
								<span class="truncate text-base font-medium text-ink-gray-9">{{
									collaborator.email
								}}</span>
								<Badge
									v-if="collaborator.status === 'Pending'"
									size="sm"
									theme="amber"
									:label="__('Invited')"
								/>
							</div>
							<div class="flex flex-wrap gap-1">
								<Badge
									v-for="section in grantedSections(levelsOf(collaborator))"
									:key="section.key"
									:variant="section.level === 'Edit' ? 'subtle' : 'outline'"
									:label="__(section.label)"
									:title="section.level === 'Edit' ? __('Can edit') : __('Can view')"
								>
									<template #prefix>
										<Icon
											:icon="section.level === 'Edit' ? 'lucide-pencil' : 'lucide-eye'"
											class="size-3"
											aria-hidden="true"
										/>
									</template>
								</Badge>
							</div>
						</div>
					</button>

					<Dropdown :options="actionsFor(collaborator)" align="end">
						<Button variant="ghost" :label="__('Collaborator actions')">
							<template #icon>
								<span class="lucide-ellipsis size-4" />
							</template>
						</Button>
					</Dropdown>
				</li>
			</TransitionGroup>
		</div>

		<CollaboratorDrawer
			v-model:open="isDrawerOpen"
			:event="event"
			:collaborator="editing"
			:taken="taken"
			@success="collaborators.reload()"
			@revoke="confirmRevoke"
		/>
	</section>
</template>

<style scoped>
/* The leaving row is taken out of flow so the rows below close the gap at once. */
.collaborator-leave-active {
	position: absolute;
	inset-inline: 0;
	transition:
		opacity 150ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 150ms cubic-bezier(0.23, 1, 0.32, 1);
}

.collaborator-leave-to {
	opacity: 0;
	transform: translateX(0.5rem);
}

.collaborator-move {
	transition: transform 250ms cubic-bezier(0.23, 1, 0.32, 1);
}

@media (prefers-reduced-motion: reduce) {
	.collaborator-leave-to {
		transform: none;
	}

	.collaborator-move {
		transition: none;
	}
}
</style>
