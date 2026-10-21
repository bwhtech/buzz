<script setup lang="ts">
import { useStorage } from "@vueuse/core"
import { Button, useCall } from "frappe-ui"
import { computed, watch } from "vue"

interface ChecklistStep {
	name: string
	title: string
	persona: string
	path: string
	completed: boolean
}

const checklist = useCall<ChecklistStep[]>({
	url: "/api/v2/method/buzz.api.playground.get_checklist",
})
const steps = computed(() => checklist.data ?? [])
const done = computed(() => steps.value.filter((step) => step.completed).length)
const allDone = computed(() => steps.value.length > 0 && done.value === steps.value.length)

// Open on desktop, a pill on phones where the card would cover the page.
const open = useStorage("playground-checklist-open", window.innerWidth >= 640)
watch(open, (isOpen) => isOpen && checklist.reload())

const switchPersona = useCall<{ redirect_to: string }, { persona: string; redirect_to: string }>({
	url: "/api/v2/method/buzz.api.playground.switch_persona",
	method: "POST",
	immediate: false,
	onSuccess: (data) => window.location.assign(data.redirect_to),
})

const personaLabels: Record<string, string> = {
	organizer: __("Organizer"),
	attendee: __("Attendee"),
	front_desk: __("Front desk"),
}
</script>

<template>
	<!-- The pill shares the bar's row; the open card sits above the bar so neither covers the other. -->
	<div
		v-if="steps.length"
		class="fixed right-4 z-50"
		:class="open ? 'bottom-36 sm:bottom-20' : 'bottom-20 sm:bottom-4'"
	>
		<Button
			v-if="!open"
			class="rounded-full shadow-xl"
			:aria-label="__('Getting started')"
			:icon-left="allDone ? 'lucide-circle-check' : 'lucide-list-checks'"
			@click="open = true"
		>
			<span class="hidden sm:inline">{{ __("Getting started") }}</span>
			<span class="tabular-nums text-ink-gray-5 sm:ml-1">{{ done }}/{{ steps.length }}</span>
		</Button>
		<section
			v-else
			class="flex w-80 flex-col gap-1 rounded-5 border border-outline-gray-2 bg-surface-elevation-2 p-2 shadow-xl"
			:aria-label="__('Getting started')"
		>
			<div class="flex items-start gap-2 px-2 pb-2 pt-1">
				<div class="flex min-w-0 flex-1 flex-col gap-0.5">
					<span class="text-base-semibold text-ink-gray-9">
						{{ allDone ? __("You've tried it all") : __("Try Buzz end to end") }}
					</span>
					<span class="text-sm text-ink-gray-6">
						{{
							__("{0} of {1} done. Each step switches you to the right person.", [
								done,
								steps.length,
							])
						}}
					</span>
				</div>
				<Button
					variant="ghost"
					icon="lucide-minus"
					:aria-label="__('Minimize')"
					@click="open = false"
				/>
			</div>
			<button
				v-for="step in steps"
				:key="step.name"
				class="flex items-center gap-3 rounded px-2 py-2 text-left hover:bg-surface-gray-2 disabled:opacity-60"
				:disabled="switchPersona.loading"
				@click="switchPersona.submit({ persona: step.persona, redirect_to: step.path })"
			>
				<span
					class="size-4 shrink-0"
					:class="
						step.completed
							? 'lucide-circle-check text-ink-green-6'
							: 'lucide-circle text-ink-gray-4'
					"
				/>
				<span class="flex min-w-0 flex-1 flex-col">
					<span
						class="text-base"
						:class="step.completed ? 'text-ink-gray-5 line-through' : 'text-ink-gray-8'"
					>
						{{ step.title }}
					</span>
					<span class="text-sm text-ink-gray-5">{{ personaLabels[step.persona] }}</span>
				</span>
				<span class="lucide-chevron-right size-4 shrink-0 text-ink-gray-4" />
			</button>
		</section>
	</div>
</template>
