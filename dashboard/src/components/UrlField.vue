<script setup lang="ts">
// A web address field: the fixed start of the address above the part that can be edited.
withDefaults(
	defineProps<{
		prefix: string
		label: string
		placeholder?: string
		// Matches frappe-ui's TextInput variants, to sit among other inputs.
		variant?: "outline" | "subtle"
	}>(),
	{ placeholder: undefined, variant: "outline" },
)

const VARIANTS = {
	outline: "border-outline-gray-2 focus-within:border-outline-gray-4",
	subtle:
		"border-[--surface-gray-2] bg-surface-gray-2 hover:bg-surface-gray-3 focus-within:border-outline-gray-4 focus-within:bg-surface-base focus-within:shadow-sm",
}
const path = defineModel<string>({ default: "" })
</script>

<template>
	<!-- Host on its own line so a long slug keeps the full width to itself. The border
		 lights up on focus-within: the whole box is the field, not just the input. -->
	<div
		class="rounded-4 border px-2.5 py-1.5 transition-colors duration-150 ease-out motion-reduce:transition-none"
		:class="VARIANTS[variant]"
	>
		<p class="truncate text-xs leading-4 text-ink-gray-5">{{ prefix }}</p>
		<input
			v-model="path"
			:aria-label="label"
			:placeholder="placeholder"
			class="w-full bg-transparent text-base text-ink-gray-8 placeholder:text-ink-gray-4 focus:outline-none"
		/>
	</div>
</template>
