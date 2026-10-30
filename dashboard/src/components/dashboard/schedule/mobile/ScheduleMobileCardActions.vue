<script setup lang="ts">
defineEmits<{ edit: []; press: [event: PointerEvent] }>()
</script>

<template>
	<div class="-my-1 -mr-1.5 flex shrink-0 items-center text-ink-gray-5">
		<button
			type="button"
			aria-label="Edit"
			class="grid size-8 place-items-center rounded-4 active:bg-surface-gray-3"
			@click.stop="$emit('edit')"
		>
			<span class="lucide-pen size-4" aria-hidden="true" />
		</button>
		<div
			role="button"
			aria-label="Drag to move"
			class="grid size-8 touch-none place-items-center rounded-4 active:bg-surface-gray-3"
			@pointerdown="$emit('press', $event)"
			@click.stop
		>
			<span class="lucide-grip-vertical size-4" aria-hidden="true" />
		</div>
	</div>
</template>
