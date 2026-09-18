<script setup lang="ts">
import { Button } from "frappe-ui"

defineProps<{ disabled?: boolean }>()
defineEmits<{ discard: []; save: [] }>()
</script>

<template>
	<div class="save-bar flex items-center gap-2">
		<Button
			variant="solid"
			size="md"
			label="Save changes"
			:disabled="disabled"
			@click="$emit('save')"
		/>
		<Button size="md" label="Cancel" @click="$emit('discard')" />
	</div>
</template>

<style scoped>
.save-bar {
	animation: save-bar-in 200ms cubic-bezier(0.23, 1, 0.32, 1);
}

@keyframes save-bar-in {
	from {
		opacity: 0;
		transform: translateY(0.5rem);
	}
}

@media (prefers-reduced-motion: reduce) {
	.save-bar {
		animation: none;
	}
}
</style>
