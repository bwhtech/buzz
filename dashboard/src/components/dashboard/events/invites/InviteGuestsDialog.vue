<script setup lang="ts">
import { Button, Dialog, LoadingText, SidebarItem, SidebarSection } from "frappe-ui"
import { computed, ref } from "vue"

import { useIsMobile } from "@/composables/useIsMobile"

import InviteEmailsPane from "./InviteEmailsPane.vue"
import InviteMessageStep from "./InviteMessageStep.vue"
import InviteMobileFlow from "./InviteMobileFlow.vue"
import InviteReviewStep from "./InviteReviewStep.vue"
import type { TierOption } from "./invites"
import InviteStepActions from "./InviteStepActions.vue"
import PastEventGuests from "./PastEventGuests.vue"
import { stageTitle, useInviteFlow } from "./useInviteFlow"

const props = defineProps<{ event: string; eventTitle: string; tiers: TierOption[] }>()
const open = defineModel<boolean>({ required: true })
const emit = defineEmits<{ sent: [] }>()

const isMobile = useIsMobile()
const flow = useInviteFlow(
	props.event,
	() => props.tiers,
	() => {
		emit("sent")
		open.value = false
	},
)
const { selection, stage, direction, message, attempted, pastEvents, defaultTier } = flow
const { selected } = selection
const source = ref("emails")
const body = ref<HTMLElement>()
const emailsPane = ref<InstanceType<typeof InviteEmailsPane>>()
const openEvent = computed(() => pastEvents.data?.find((row) => String(row.name) === source.value))

// Undo is the dialog's while the box is empty or holds only what undo put back; once
// the user edits the text, the browser's own undo takes over.
function onKeydown(keyEvent: KeyboardEvent) {
	if (stage.value !== "pick") return
	const mod = keyEvent.metaKey || keyEvent.ctrlKey
	if (mod && keyEvent.key === "z" && !keyEvent.shiftKey) undo(keyEvent)
	else if (keyEvent.shiftKey && keyEvent.key === "Enter") {
		keyEvent.preventDefault()
		emailsPane.value?.commit()
	}
}

function undo(keyEvent: KeyboardEvent) {
	if (emailsPane.value && !emailsPane.value.ownsUndo()) return
	const change = selection.undo()
	if (!change) return
	keyEvent.preventDefault()
	if ("added" in change && change.typed)
		emailsPane.value?.restore(change.added.map((invitee) => invitee.email))
}

function reset() {
	source.value = "emails"
	flow.reset()
}
</script>

<template>
	<InviteMobileFlow
		v-if="isMobile"
		v-model="open"
		:flow="flow"
		:event="event"
		:event-title="eventTitle"
		:tiers="tiers"
	/>
	<Dialog v-else v-model="open" bare size="4xl" @after-leave="reset">
		<div class="flex h-[min(42rem,85vh)] flex-col" @keydown="onKeydown">
			<header class="flex items-center gap-2 border-b border-outline-gray-1 px-5 py-3">
				<Button
					v-if="stage !== 'pick'"
					variant="ghost"
					icon="lucide-arrow-left"
					label="Back"
					@click="flow.back"
				/>
				<h3 class="flex-1 text-lg font-semibold text-ink-gray-9">
					{{ stageTitle(stage, selected.length) }}
				</h3>
				<Button variant="ghost" icon="lucide-x" label="Close" @click="open = false" />
			</header>

			<div ref="body" class="flex min-h-0 flex-1 flex-col">
				<Transition :name="`invite-stage-${direction}`" mode="out-in">
					<div
						v-if="stage === 'pick'"
						key="pick"
						class="grid min-h-0 flex-1 grid-cols-[14rem_minmax(0,1fr)]"
					>
						<nav
							class="overflow-y-auto border-r border-outline-gray-1 p-2"
							aria-label="Where to invite from"
						>
							<SidebarSection>
								<SidebarItem
									label="Enter emails"
									icon="lucide-at-sign"
									:active="source === 'emails'"
									:on-click="() => (source = 'emails')"
								/>
							</SidebarSection>
							<SidebarSection label="Past events">
								<LoadingText v-if="pastEvents.loading && !pastEvents.data" class="px-2 py-1.5" />
								<p
									v-else-if="!pastEvents.data?.length"
									class="px-2 py-1.5 text-p-sm text-ink-gray-5"
								>
									This is your first event.
								</p>
								<SidebarItem
									v-for="row in pastEvents.data"
									:key="row.name"
									:label="row.title"
									icon="lucide-calendar"
									:active="source === String(row.name)"
									:on-click="() => (source = String(row.name))"
								/>
							</SidebarSection>
						</nav>

						<div class="min-h-0 overflow-y-auto px-5 py-4">
							<InviteEmailsPane
								v-if="source === 'emails'"
								ref="emailsPane"
								:event="event"
								:selection="selection"
								:tiers="tiers"
								:default-tier="defaultTier"
							/>
							<PastEventGuests
								v-else-if="openEvent"
								:key="source"
								:event="source"
								:title="openEvent.title"
								:is-selected="selection.isSelected"
								@toggle="flow.toggle"
								@select-all="selection.add"
							/>
						</div>
					</div>
					<InviteReviewStep
						v-else-if="stage === 'review'"
						key="review"
						v-model="selected"
						:tiers="tiers"
						:attempted="attempted"
						@remove="(invitee) => selection.remove([invitee])"
					/>
					<InviteMessageStep
						v-else
						key="message"
						v-model="message"
						:event="event"
						:event-title="eventTitle"
					/>
				</Transition>
			</div>

			<InviteStepActions :flow="flow" @add-directly="flow.addDirectly(body)" />
		</div>
	</Dialog>
</template>

<style>
/* Unscoped: the phone page uses the same step transition. */
.invite-stage-forward-enter-active,
.invite-stage-back-enter-active {
	transition:
		opacity 200ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
.invite-stage-forward-leave-active,
.invite-stage-back-leave-active {
	transition: opacity 100ms ease-out;
}
.invite-stage-forward-enter-from {
	opacity: 0;
	transform: translateX(12px);
}
.invite-stage-back-enter-from {
	opacity: 0;
	transform: translateX(-12px);
}
.invite-stage-forward-leave-to,
.invite-stage-back-leave-to {
	opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
	.invite-stage-forward-enter-from,
	.invite-stage-back-enter-from {
		transform: none;
	}
}
</style>
