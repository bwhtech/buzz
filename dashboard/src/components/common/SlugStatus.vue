<script setup lang="ts">
import { LoadingText } from "frappe-ui"

import type { Availability } from "@/composables/useSlugAvailability"

defineProps<{ checking: boolean; availability: Availability | null }>()
</script>

<template>
	<!-- Always one line tall, with the states stacked so they crossfade in place: a line that
	     came and went would shift everything below it while the check runs. -->
	<div class="relative h-[1lh]">
		<Transition
			enter-active-class="transition duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
			enter-from-class="opacity-0"
			leave-active-class="transition duration-100 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
			leave-to-class="opacity-0"
		>
			<LoadingText
				v-if="checking"
				key="checking"
				class="absolute inset-0 !text-[length:inherit]"
				:text="__('Checking availability')"
			/>
			<p
				v-else-if="availability"
				key="answer"
				class="absolute inset-0 flex items-center gap-1"
				:class="availability.available ? 'text-ink-green-6' : 'text-ink-amber-7'"
			>
				<span
					class="size-3.5 shrink-0"
					:class="availability.available ? 'lucide-check' : 'lucide-triangle-alert'"
					aria-hidden="true"
				/>
				<span class="truncate">{{ availability.message }}</span>
			</p>
			<span v-else key="hint" class="absolute inset-0 truncate">
				<slot />
			</span>
		</Transition>
	</div>
</template>
