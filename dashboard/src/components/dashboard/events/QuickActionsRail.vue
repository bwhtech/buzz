<script lang="ts">
export type QuickAction = {
	icon: string
	label: string
	link?: string
	loading?: boolean
	onClick?: () => void
}
</script>

<script setup lang="ts">
import { Button } from "frappe-ui"

defineProps<{
	// What is open or closed — "Registration", "Proposals".
	subject: string
	closed: boolean
	canWrite: boolean
	openIcon: string
	closedIcon: string
	actions: QuickAction[]
}>()
defineEmits<{ toggle: [] }>()

// Every control in the rail answers a press the same way; the string is written once.
const PRESSABLE =
	"duration-150 ease-out active:scale-[0.98] !transition-[transform,background-color,color]"
</script>

<template>
	<h3 class="text-p-sm font-medium text-ink-gray-5">Quick actions</h3>
	<!-- The whole block is the control: the state is the label, pressing it is how the
		 state gets changed, and the icon tile carries the state before the words are read.
		 A reader the server would refuse gets it as a readout instead — read access alone
		 is a Viewer or Frontdesk, who cannot write the event. -->
	<Button
		:class="`h-auto w-full !justify-start !gap-3 px-2.5 py-2.5 ${PRESSABLE}`"
		variant="subtle"
		:disabled="!canWrite"
		theme="gray"
		@click="$emit('toggle')"
	>
		<template #prefix>
			<span class="relative grid size-9 shrink-0 place-items-center">
				<!-- Only while open: the halo says the page is taking submissions right now,
					 and a closed state has nothing to keep announcing. -->
				<span
					v-if="!closed"
					class="absolute inset-0 animate-ping rounded-4 bg-surface-green-7 opacity-25 [animation-duration:2.5s] motion-reduce:hidden"
					aria-hidden="true"
				/>
				<span
					class="relative grid size-9 place-items-center rounded-4 text-white"
					:class="closed ? 'bg-surface-red-7' : 'bg-surface-green-7'"
				>
					<span class="size-5" :class="closed ? closedIcon : openIcon" aria-hidden="true" />
				</span>
			</span>
		</template>
		<span class="flex flex-col items-start">
			<span class="text-p-base font-medium">{{ subject }}</span>
			<span class="text-p-sm opacity-70">{{ closed ? "Closed" : "Open" }}</span>
		</span>
	</Button>

	<section class="space-y-1 pt-1">
		<Button
			v-for="action in actions"
			:key="action.label"
			:class="`w-full !justify-start ${PRESSABLE}`"
			variant="ghost"
			:label="action.label"
			:link="action.link"
			:loading="action.loading"
			@click="action.onClick?.()"
		>
			<template #prefix>
				<span :class="[action.icon, 'size-4']" aria-hidden="true" />
			</template>
		</Button>
	</section>
</template>
