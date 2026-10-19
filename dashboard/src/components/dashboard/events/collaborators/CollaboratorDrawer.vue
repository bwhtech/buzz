<script setup lang="ts">
import { Avatar, Badge, Button, ErrorMessage, FormLabel, Icon, toast } from "frappe-ui"
import { computed, nextTick, ref, useId, watch } from "vue"

import {
	Drawer,
	DrawerCloseButton,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import CollaboratorAccessFields from "@/components/dashboard/events/collaborators/CollaboratorAccessFields.vue"
import EmailChipsInput from "@/components/dashboard/events/collaborators/EmailChipsInput.vue"
import { useInviteCollaborators, useUpdateCollaboratorAccess } from "@/data/collaborators"
import type { EventCollaborator } from "@/types"
import { emptySectionLevels, levelsOf, opensAPage } from "@/utils/eventSections"
import { serverErrorMessage } from "@/utils/serverError"

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// No collaborator means a new invitation. `taken` holds addresses already on the list.
const props = defineProps<{
	event: string
	collaborator: EventCollaborator | null
	taken: string[]
}>()
const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ success: []; revoke: [collaborator: EventCollaborator] }>()

const inviteCollaborators = useInviteCollaborators()
const updateAccess = useUpdateCollaboratorAccess()

const emails = ref<string[]>([])
const draft = ref("")
const levels = ref(emptySectionLevels())
const savedLevels = ref("")
const errorMessage = ref("")
const chipsInput = ref<InstanceType<typeof EmailChipsInput>>()
const emailInputId = useId()

const isInvite = computed(() => !props.collaborator)
const isPending = computed(() => props.collaborator?.status === "Pending")

watch(open, async (isOpen) => {
	if (!isOpen) return
	emails.value = []
	draft.value = ""
	errorMessage.value = ""
	levels.value = props.collaborator ? levelsOf(props.collaborator) : emptySectionLevels()
	savedLevels.value = JSON.stringify(levels.value)
	await nextTick()
	chipsInput.value?.focus()
})

function rejected(email: string) {
	if (!EMAIL_PATTERN.test(email)) return __("Not a valid email address")
	if (props.taken.includes(email.toLowerCase())) return __("Already has access")
	return ""
}

// What is still being typed counts, so Enter on a single address sends it.
const addresses = computed(() => {
	const typed = [...emails.value, ...draft.value.split(/[\s,;]+/).filter(Boolean)]
	return [...new Map(typed.map((email) => [email.toLowerCase(), email])).values()]
})

const firstRejection = computed(() => {
	const email = emails.value.find(rejected)
	return email ? `${email}: ${rejected(email)}` : ""
})

const canSubmit = computed(() => {
	if (!opensAPage(levels.value)) return false
	if (!isInvite.value) return JSON.stringify(levels.value) !== savedLevels.value
	return addresses.value.length > 0 && addresses.value.every((email) => !rejected(email))
})

const primaryLabel = computed(() => {
	if (!isInvite.value) return __("Save changes")
	const count = addresses.value.length
	return count > 1 ? __("Send {0} invites", [count]) : __("Send invite")
})

const isSaving = computed(() => inviteCollaborators.loading || updateAccess.loading)

async function submit() {
	if (!canSubmit.value || isSaving.value) return
	const error = await (isInvite.value ? sendInvites() : saveAccess())
	errorMessage.value = serverErrorMessage(error)
	if (error) return
	emit("success")
	open.value = false
}

async function sendInvites() {
	const count = addresses.value.length
	await inviteCollaborators
		.submit({
			event: props.event,
			invites: addresses.value.map((email) => ({ email, ...levels.value })),
		})
		.catch(() => null)
	if (!inviteCollaborators.error)
		toast.success(count > 1 ? __("{0} invitations sent", [count]) : __("Invitation sent"))
	return inviteCollaborators.error
}

async function saveAccess() {
	const collaborator = props.collaborator as EventCollaborator
	await updateAccess
		.submit({ event: props.event, email: collaborator.email, sections: levels.value })
		.catch(() => null)
	if (!updateAccess.error) toast.success(__("Access updated for {0}", [collaborator.email]))
	return updateAccess.error
}
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent>
			<div
				class="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-outline-gray-1 pl-5 pr-2.5"
			>
				<DrawerTitle class="text-lg font-semibold text-ink-gray-9">
					{{ isInvite ? __("Invite collaborators") : __("Edit access") }}
				</DrawerTitle>
				<DrawerDescription class="sr-only">
					{{ __("Collaborators see only this event, and only the sections you choose.") }}
				</DrawerDescription>
				<DrawerCloseButton />
			</div>

			<div
				class="flex flex-1 flex-col gap-5 overflow-y-auto overscroll-contain p-5"
				@keydown.meta.enter.prevent="submit"
				@keydown.ctrl.enter.prevent="submit"
			>
				<div v-if="collaborator" class="flex items-center gap-3">
					<Avatar :label="collaborator.email" size="xl" />
					<div class="flex min-w-0 flex-col gap-0.5">
						<div class="flex items-center gap-2">
							<span class="truncate text-base font-medium text-ink-gray-9">{{
								collaborator.email
							}}</span>
							<Badge v-if="isPending" size="sm" theme="amber" :label="__('Invited')" />
						</div>
						<span class="text-sm text-ink-gray-5">
							{{ isPending ? __("Hasn't accepted yet") : __("Has accepted") }}
						</span>
					</div>
				</div>

				<div v-else class="flex flex-col gap-1.5">
					<FormLabel :id="emailInputId" :label="__('Email')" />
					<EmailChipsInput
						:id="emailInputId"
						ref="chipsInput"
						v-model="emails"
						v-model:draft="draft"
						:rejected="rejected"
						@keydown.enter.exact="(event: KeyboardEvent) => event.defaultPrevented || submit()"
					/>
					<ErrorMessage v-if="firstRejection" :message="firstRejection" />
					<span v-else class="text-xs text-ink-gray-5">
						{{ __("Press Enter or comma to add. Paste a list to add several at once.") }}
					</span>
				</div>

				<CollaboratorAccessFields v-model="levels" />
				<ErrorMessage :message="errorMessage" />
			</div>

			<template #footer>
				<Button
					v-if="collaborator"
					variant="ghost"
					theme="red"
					:label="isPending ? __('Retract invite') : __('Revoke access')"
					@click="emit('revoke', collaborator)"
				/>
				<span v-else class="flex min-w-0 items-center gap-1.5 text-sm text-ink-gray-5">
					<Icon icon="lucide-lock" class="size-3.5 shrink-0" aria-hidden="true" />
					{{ __("Sees only this event") }}
				</span>
				<div class="ml-auto flex gap-2">
					<Button variant="subtle" :label="__('Cancel')" @click="open = false" />
					<Button
						variant="solid"
						:label="primaryLabel"
						:disabled="!canSubmit"
						:loading="isSaving"
						@click="submit"
					/>
				</div>
			</template>
		</DrawerContent>
	</Drawer>
</template>
