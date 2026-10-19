<script setup lang="ts">
import { watchDebounced } from "@vueuse/core"
import { LoadingText } from "frappe-ui"
import { ref, watch } from "vue"

import PrefixedInput from "@/components/common/PrefixedInput.vue"

export type Availability = { available: boolean; message: string }

const props = defineProps<{
	prefix: string
	label: string
	placeholder?: string
	disabled?: boolean
	// The slug already saved, which needs no check.
	savedSlug?: string | null
	check: (slug: string) => Promise<Availability | null>
}>()
const slug = defineModel<string>({ required: true })
// Null while unchecked or checking.
const availability = defineModel<Availability | null>("availability", { default: null })
const checking = ref(false)

const needsCheck = (value: string) => Boolean(value.trim() && value !== props.savedSlug)

watch(
	slug,
	(value) => {
		availability.value = null
		checking.value = needsCheck(value)
	},
	{ immediate: true },
)

watchDebounced(
	slug,
	async (value) => {
		if (!needsCheck(value)) return
		// A failed check says nothing rather than spinning forever; the save still checks.
		const answer = await props.check(value).catch(() => null)
		// A later keystroke may have overtaken this request while it was in flight.
		if (slug.value !== value) return
		checking.value = false
		availability.value = answer
	},
	{ debounce: 400, immediate: true },
)
</script>

<template>
	<div>
		<PrefixedInput
			v-model="slug"
			:prefix="prefix"
			:label="label"
			:placeholder="placeholder"
			:disabled="disabled"
		/>
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
				class="pt-1.5 !text-sm"
				:text="__('Checking availability')"
			/>
			<p
				v-else-if="availability"
				key="answer"
				class="flex items-center gap-1 pt-1.5 text-sm"
				:class="availability.available ? 'text-ink-green-6' : 'text-ink-amber-7'"
			>
				<span
					class="size-3.5 shrink-0"
					:class="availability.available ? 'lucide-check' : 'lucide-triangle-alert'"
					aria-hidden="true"
				/>
				{{ availability.message }}
			</p>
		</Transition>
	</div>
</template>
