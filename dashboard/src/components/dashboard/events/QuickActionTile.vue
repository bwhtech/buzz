<script lang="ts">
export type TileTone = "green" | "red" | "amber" | "gray" | "violet"

// Every control in the rail answers a press the same way; the string is written once.
export const PRESSABLE =
	"duration-150 ease-out active:scale-[0.98] !transition-[transform,background-color,color]"

const TONES: Record<TileTone, string> = {
	green: "bg-surface-green-7",
	red: "bg-surface-red-7",
	amber: "bg-surface-amber-7",
	gray: "bg-surface-gray-7",
	violet: "bg-surface-violet-7",
}
</script>

<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed } from "vue"

const props = withDefaults(
	defineProps<{
		icon: string
		title: string
		subtitle: string
		tone: TileTone
		disabled?: boolean
		// The halo says the thing is live right now; a settled state has nothing to announce.
		pulse?: boolean
	}>(),
	{ disabled: false, pulse: false },
)
defineEmits<{ click: [] }>()

const toneClass = computed(() => TONES[props.tone])
</script>

<template>
	<!-- The whole block is the control: the state is the label, pressing it is how the
		 state gets changed, and the icon tile carries the state before the words are read.
		 A reader the server would refuse gets it as a readout instead. -->
	<Button
		:class="`h-auto w-full !justify-start !gap-3 px-2.5 py-2.5 ${PRESSABLE}`"
		variant="subtle"
		theme="gray"
		:disabled="disabled"
		@click="$emit('click')"
	>
		<template #prefix>
			<span class="relative grid size-9 shrink-0 place-items-center">
				<span
					v-if="pulse"
					class="absolute inset-0 animate-ping rounded-4 opacity-25 [animation-duration:2.5s] motion-reduce:hidden"
					:class="toneClass"
					aria-hidden="true"
				/>
				<span
					class="relative grid size-9 place-items-center rounded-4 text-white"
					:class="toneClass"
				>
					<span class="size-5" :class="icon" aria-hidden="true" />
				</span>
			</span>
		</template>
		<span class="flex flex-col items-start">
			<span class="text-p-base font-medium">{{ title }}</span>
			<span class="text-p-sm opacity-70">{{ subtitle }}</span>
		</span>
	</Button>
</template>
