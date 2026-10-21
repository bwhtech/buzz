<script setup lang="ts">
import { useDocumentVisibility, useIntervalFn, useSessionStorage, useStorage } from "@vueuse/core"
import { Badge, Button, TabButtons, useCall } from "frappe-ui"
import { computed, onBeforeUnmount, ref, watch } from "vue"
import { useRouter } from "vue-router"

import { useIsMobile } from "@/composables/useIsMobile"

import {
	type ChecklistGroup,
	type ChecklistStep,
	useBrowserCompletedSteps,
	useSpotlightStep,
} from "./checklist"
import PlaygroundStepDetail from "./PlaygroundStepDetail.vue"

const checklist = useCall<ChecklistGroup[]>({
	url: "/api/v2/method/buzz.api.playground.get_checklist",
})

// Open on desktop, a pill on phones where the card would cover the page.
const open = useStorage("playground-checklist-open", window.innerWidth >= 640)
watch(open, (isOpen) => isOpen && checklist.reload())

// A pill while the spotlight shows, so the card never covers the control it points at.
const spotlightStep = useSpotlightStep()
const showCard = computed(() => open.value && !spotlightStep.value)
function openCard() {
	spotlightStep.value = null
	open.value = true
}

// The bar outlives dashboard navigation, so reload after each route change. Public pages
// have no router: every visit there is a full page load.
const removeRouteHook = useRouter()?.afterEach(() => checklist.reload())
onBeforeUnmount(() => removeRouteHook?.())

// Actions inside one page (opening registrations, accepting a proposal) change no route.
// ponytail: polling while open and visible; a realtime push per doc change if load matters.
const visibility = useDocumentVisibility()
useIntervalFn(() => open.value && visibility.value === "visible" && checklist.reload(), 10000)

const stepFilter = useStorage<"essentials" | "everything">(
	"playground-checklist-length",
	"essentials",
)
const stepFilterOptions = [
	{ label: __("Essentials"), value: "essentials" },
	{ label: __("Everything"), value: "everything" },
]

const browserCompleted = useBrowserCompletedSteps()
const isDone = (step: ChecklistStep) =>
	step.completed || browserCompleted.names.value.includes(step.name)

const groups = computed(() =>
	(checklist.data ?? []).map((group) => ({
		...group,
		steps: group.steps.filter((step) => stepFilter.value === "everything" || !step.optional),
	})),
)
const steps = computed(() => groups.value.flatMap((group) => group.steps))
const done = computed(() => steps.value.filter(isDone).length)
const allDone = computed(() => steps.value.length > 0 && done.value === steps.value.length)
const groupDone = (group: ChecklistGroup) => group.steps.filter(isDone).length

// Per session, so the group stays open across the reload a persona switch makes.
// Unset, the first group with work left opens.
const COLLAPSED = "collapsed"
const openGroup = useSessionStorage("playground-checklist-group", "")
const currentGroup = computed(() => {
	if (openGroup.value === COLLAPSED) return undefined
	return (
		openGroup.value || groups.value.find((group) => groupDone(group) < group.steps.length)?.name
	)
})
const toggleGroup = (name: string) => {
	openGroup.value = currentGroup.value === name ? COLLAPSED : name
}

const isMobile = useIsMobile()
const activeStep = ref<ChecklistStep>()
const container = ref<HTMLElement>()
const detail = ref<HTMLElement>()
const detailTop = ref(0)

let pendingDetail: ReturnType<typeof setTimeout> | undefined

// With a card open, wait before switching: the pointer crosses other rows on its way to the card.
function hoverStep(step: ChecklistStep, event: MouseEvent) {
	if (isMobile.value) return
	const row = event.currentTarget as HTMLElement
	clearTimeout(pendingDetail)
	if (!activeStep.value) showDetail(step, row)
	else pendingDetail = setTimeout(() => showDetail(step, row), 200)
}

function cancelPendingDetail() {
	clearTimeout(pendingDetail)
}

function hideDetail() {
	cancelPendingDetail()
	activeStep.value = undefined
}

// Level with the hovered row, kept inside the panel's height so it never runs off screen.
function showDetail(step: ChecklistStep, rowElement: HTMLElement) {
	if (!container.value) return
	const row = rowElement.getBoundingClientRect()
	const rowTop = row.top - container.value.getBoundingClientRect().top - 12
	const maxTop = container.value.offsetHeight - (detail.value?.offsetHeight ?? 150)
	detailTop.value = Math.max(0, Math.min(rowTop, maxTop))
	activeStep.value = step
}

const switchPersona = useCall<{ redirect_to: string }, { persona: string; redirect_to: string }>({
	url: "/api/v2/method/buzz.api.playground.switch_persona",
	method: "POST",
	immediate: false,
	onSuccess: (data) => window.location.assign(data.redirect_to),
})

function go(step: ChecklistStep) {
	openGroup.value = groups.value.find((group) => group.steps.includes(step))?.name ?? ""
	if (step.completes_on === "visit") browserCompleted.add(step.name)
	if (step.target) spotlightStep.value = step
	switchPersona.submit({ persona: step.persona, redirect_to: step.path })
}

function selectStep(step: ChecklistStep) {
	// Phones show the detail inline, so a tap opens it; desktop goes straight there.
	if (isMobile.value) activeStep.value = activeStep.value?.name === step.name ? undefined : step
	else if (!step.locked) go(step)
}
</script>

<template>
	<!-- The pill shares the bar's row; the open card sits above the bar so neither covers the other. -->
	<div
		v-if="groups.length"
		ref="container"
		data-playground
		class="fixed right-4 z-50"
		:class="open ? 'bottom-36 sm:bottom-20' : 'bottom-20 sm:bottom-4'"
		@mouseleave="hideDetail"
	>
		<Button
			v-if="!showCard"
			class="rounded-full shadow-xl"
			:aria-label="__('Getting started')"
			:icon-left="allDone ? 'lucide-circle-check' : 'lucide-list-checks'"
			@click="openCard"
		>
			<span class="hidden sm:inline">{{ __("Getting started") }}</span>
			<span class="tabular-nums text-ink-gray-5 sm:ml-1">{{ done }}/{{ steps.length }}</span>
		</Button>
		<template v-else>
			<!-- Padding, not margin: the gap stays inside the hover area so the pointer can cross it. -->
			<div
				v-if="activeStep && !isMobile"
				ref="detail"
				class="absolute right-full pr-2"
				:style="{ top: `${detailTop}px` }"
				@mouseenter="cancelPendingDetail"
			>
				<div
					class="w-64 rounded-5 border border-outline-gray-2 bg-surface-elevation-2 p-4 shadow-xl"
				>
					<PlaygroundStepDetail :step="activeStep" :loading="switchPersona.loading" @go="go" />
				</div>
			</div>
			<section
				class="flex max-h-[calc(100vh-12rem)] w-80 flex-col rounded-5 border border-outline-gray-2 bg-surface-elevation-2 shadow-xl"
				:aria-label="__('Getting started')"
			>
				<div class="flex flex-col gap-3 border-b border-outline-gray-1 p-4 pb-3">
					<div class="flex items-start gap-2">
						<div class="flex min-w-0 flex-1 flex-col gap-0.5">
							<span class="text-base-semibold text-ink-gray-9">
								{{ allDone ? __("You've tried it all") : __("Try Buzz end to end") }}
							</span>
							<span class="text-sm text-ink-gray-6">
								{{ __("Each step switches you to the right person.") }}
							</span>
						</div>
						<Button
							variant="ghost"
							icon="lucide-chevron-down"
							:aria-label="__('Minimize')"
							@click="open = false"
						/>
					</div>
					<TabButtons v-model="stepFilter" fluid :options="stepFilterOptions" />
				</div>
				<div class="flex flex-col gap-0.5 overflow-y-auto p-2">
					<div v-for="group in groups" :key="group.name" class="flex flex-col">
						<button
							class="flex items-center gap-2 rounded px-2 py-2 text-left hover:bg-surface-gray-2"
							:aria-expanded="currentGroup === group.name"
							@click="toggleGroup(group.name)"
						>
							<span class="flex-1 text-base-medium text-ink-gray-8">{{ group.title }}</span>
							<span class="text-sm tabular-nums text-ink-gray-5">
								{{ groupDone(group) }}/{{ group.steps.length }}
							</span>
							<span
								class="lucide-chevron-right size-4 text-ink-gray-4 transition-transform"
								:class="{ 'rotate-90': currentGroup === group.name }"
							/>
						</button>
						<div v-if="currentGroup === group.name" class="flex flex-col pb-1">
							<template v-for="step in group.steps" :key="step.name">
								<button
									class="flex items-center gap-3 rounded px-2 py-1.5 text-left hover:bg-surface-gray-2 disabled:cursor-default"
									:class="{ 'bg-surface-gray-2': activeStep?.name === step.name }"
									:disabled="switchPersona.loading"
									@mouseenter="hoverStep(step, $event)"
									@click="selectStep(step)"
								>
									<!-- Both icons stay mounted so the check can transition in over the circle. -->
									<span class="relative size-4 shrink-0">
										<span
											class="absolute inset-0 transition-opacity duration-150"
											:class="[
												step.locked ? 'lucide-lock' : 'lucide-circle-dashed',
												'text-ink-gray-4',
												{ 'opacity-0': isDone(step) },
											]"
										/>
										<span
											class="checklist-check absolute inset-0 lucide-circle-check text-ink-gray-8"
											:class="{ 'checklist-check-done': isDone(step) }"
										/>
									</span>
									<span class="flex-1 text-base">
										<span
											class="checklist-title"
											:class="
												isDone(step) ? 'checklist-title-done text-ink-gray-5' : 'text-ink-gray-8'
											"
										>
											{{ step.title }}
										</span>
									</span>
									<Badge v-if="step.optional" size="sm" :label="__('Optional')" />
								</button>
								<div v-if="isMobile && activeStep?.name === step.name" class="px-2 pb-2 pl-9">
									<PlaygroundStepDetail :step="step" :loading="switchPersona.loading" @go="go" />
								</div>
							</template>
						</div>
					</div>
				</div>
				<div class="flex items-center gap-3 border-t border-outline-gray-1 px-4 py-3">
					<span class="text-sm-medium tabular-nums text-ink-gray-7">
						{{ __("{0} of {1} complete", [done, steps.length]) }}
					</span>
					<div class="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-gray-2">
						<div
							class="h-full rounded-full bg-current text-ink-gray-8 transition-[width]"
							:style="{ width: `${(done / steps.length) * 100}%` }"
						/>
					</div>
				</div>
			</section>
		</template>
	</div>
</template>

<style scoped>
/* Transitions, not keyframes: they skip the first render, so only a step that is ticked off
   while the card is on screen animates; steps already done load struck through. */
.checklist-check {
	opacity: 0;
	transform: scale(0.6);
	transition:
		opacity 150ms ease-out,
		transform 250ms cubic-bezier(0.23, 1, 0.32, 1);
}

.checklist-check-done {
	opacity: 1;
	transform: scale(1);
}

/* A line drawn left to right; as a background it follows the text across wrapped lines. */
.checklist-title {
	background: linear-gradient(currentColor, currentColor) no-repeat 0 55% / 0 1px;
	transition:
		background-size 300ms cubic-bezier(0.23, 1, 0.32, 1) 100ms,
		color 200ms ease;
}

.checklist-title-done {
	background-size: 100% 1px;
}

@media (prefers-reduced-motion: reduce) {
	.checklist-check,
	.checklist-title {
		transition-duration: 0ms;
	}
}
</style>
