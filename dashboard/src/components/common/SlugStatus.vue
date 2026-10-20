<script setup lang="ts">
import { LoadingText } from "frappe-ui"

import type { Availability } from "@/composables/useSlugAvailability"

defineProps<{ checking: boolean; availability: Availability | null }>()
</script>

<template>
	<Transition
		enter-active-class="transition duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
		enter-from-class="opacity-0 -translate-y-0.5"
		leave-active-class="transition duration-100 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
		leave-to-class="opacity-0"
		mode="out-in"
	>
		<LoadingText
			v-if="checking"
			key="checking"
			class="!text-[length:inherit]"
			:text="__('Checking availability')"
		/>
		<p
			v-else-if="availability"
			key="answer"
			class="flex items-center gap-1"
			:class="availability.available ? 'text-ink-green-6' : 'text-ink-amber-7'"
		>
			<span
				class="size-3.5 shrink-0"
				:class="availability.available ? 'lucide-check' : 'lucide-triangle-alert'"
				aria-hidden="true"
			/>
			{{ availability.message }}
		</p>
		<slot v-else />
	</Transition>
</template>
