<!-- Animates height from 0 to auto with grid rows, so content needs no measuring. -->
<template>
	<div
		class="grid transition-[grid-template-rows] duration-300 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
		:class="open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'"
		:inert="!open"
	>
		<div class="min-h-0 overflow-hidden">
			<div
				class="transition-opacity duration-200 ease-out"
				:class="open ? 'opacity-100' : 'opacity-0'"
			>
				<slot />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
defineProps<{ open: boolean }>()
</script>
