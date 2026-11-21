<script setup lang="ts">
// The title as an underlined field, so it reads as something to fill in, not a heading.
defineProps<{ invalid?: boolean; disabled?: boolean }>()
const title = defineModel<string>({ default: "" })
</script>

<template>
	<div>
		<input
			id="event-title"
			v-model="title"
			maxlength="140"
			autocomplete="off"
			:aria-label="__('Event title')"
			:placeholder="__('Name your event')"
			:disabled="disabled"
			:aria-invalid="invalid || undefined"
			class="title w-full text-[28px] font-semibold text-ink-gray-9 placeholder:text-ink-gray-4 disabled:text-ink-gray-5 md:text-4xl"
			@keydown.enter.prevent
		/>
		<p v-if="invalid" role="alert" class="mt-2 text-sm text-ink-red-7">
			{{ __("Add a title to create the event") }}
		</p>
	</div>
</template>

<style scoped>
.title {
	border: 0;
	border-bottom: 1px solid var(--outline-gray-2);
	border-radius: 0;
	background: transparent;
	padding: 0 0 12px;
	outline: none;
	box-shadow: none;
	letter-spacing: -0.01em;
	transition: border-color 150ms ease;
}
.title:not(:disabled):hover {
	border-bottom-color: var(--outline-gray-4);
}
.title:focus {
	border-bottom-color: var(--ink-gray-9);
}
.title[aria-invalid] {
	border-bottom-color: var(--ink-red-6);
}
.title[aria-invalid]::placeholder {
	color: var(--ink-red-6);
}
</style>
