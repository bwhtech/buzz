<script setup lang="ts">
// The invite flow on a phone: a full-screen page with a step header and a pinned footer.
import { onKeyStroke, useScrollLock } from "@vueuse/core"
import { Button } from "frappe-ui"
import { computed, ref, watch } from "vue"

import InviteLimitRing from "./InviteLimitRing.vue"
import InviteMessageStep from "./InviteMessageStep.vue"
import InviteMobilePick from "./InviteMobilePick.vue"
import InviteReviewStep from "./InviteReviewStep.vue"
import { INVITE_LIMIT, type TierOption } from "./invites"
import InviteStepActions from "./InviteStepActions.vue"
import { type InviteFlow, STAGES, stageTitle } from "./useInviteFlow"

const props = defineProps<{
	flow: InviteFlow
	event: string
	eventTitle: string
	tiers: TierOption[]
}>()
const open = defineModel<boolean>({ required: true })

const { selection, stage, direction, message, attempted } = props.flow
const { selected } = selection
const body = ref<HTMLElement>()
const stageIndex = computed(() => STAGES.indexOf(stage.value))

const pageLocked = useScrollLock(document.body)
watch(open, (isOpen) => (pageLocked.value = isOpen), { immediate: true })
// An open dropdown handles Escape first and marks it handled; only a bare Escape closes the page.
onKeyStroke("Escape", (keyEvent) => {
	if (open.value && !keyEvent.defaultPrevented) open.value = false
})
</script>

<template>
	<Teleport to="body">
		<Transition name="page" @after-leave="flow.reset">
			<div
				v-if="open"
				role="dialog"
				aria-modal="true"
				aria-labelledby="invite-flow-title"
				class="fixed inset-0 z-50 flex flex-col bg-surface-base"
			>
				<header class="flex items-center gap-1 border-b border-outline-gray-1 px-2 py-2">
					<Button
						v-if="stage !== 'pick'"
						variant="ghost"
						size="lg"
						icon="lucide-chevron-left"
						label="Back"
						@click="flow.back"
					/>
					<Button
						v-else
						variant="ghost"
						size="lg"
						icon="lucide-x"
						label="Close"
						@click="open = false"
					/>
					<div class="min-w-0 flex-1 px-2">
						<h3 id="invite-flow-title" class="truncate text-lg font-semibold text-ink-gray-9">
							{{ stageTitle(stage, selected.length) }}
						</h3>
						<p class="text-p-xs text-ink-gray-5">Step {{ stageIndex + 1 }} of 3</p>
					</div>
					<InviteLimitRing :used="selected.length" :limit="INVITE_LIMIT" />
					<Button
						v-if="stage !== 'pick'"
						variant="ghost"
						size="lg"
						icon="lucide-x"
						label="Close"
						@click="open = false"
					/>
				</header>
				<div class="flex h-0.5 gap-1 px-4" aria-hidden="true">
					<span
						v-for="(entry, index) in STAGES"
						:key="entry"
						class="h-full flex-1 rounded-full transition-colors duration-200 ease-out"
						:class="index <= stageIndex ? 'bg-surface-gray-9' : 'bg-surface-gray-3'"
					/>
				</div>

				<div ref="body" class="flex min-h-0 flex-1 flex-col">
					<Transition :name="`invite-stage-${direction}`" mode="out-in">
						<InviteMobilePick
							v-if="stage === 'pick'"
							key="pick"
							:flow="flow"
							:event="event"
							:tiers="tiers"
						/>
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
		</Transition>
	</Teleport>
</template>

<style scoped>
.page-enter-active {
	transition: transform 250ms cubic-bezier(0.32, 0.72, 0, 1);
}
.page-leave-active {
	transition: transform 200ms cubic-bezier(0.32, 0.72, 0, 1);
}
.page-enter-from,
.page-leave-to {
	transform: translateY(100%);
}
@media (prefers-reduced-motion: reduce) {
	.page-enter-active,
	.page-leave-active {
		transition: opacity 150ms ease-out;
	}
	.page-enter-from,
	.page-leave-to {
		transform: none;
		opacity: 0;
	}
}
</style>
