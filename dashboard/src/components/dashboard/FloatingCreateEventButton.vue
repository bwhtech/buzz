<script setup lang="ts">
import { Button } from "frappe-ui"
</script>

<template>
	<Button
		class="fixed bottom-20 right-4 z-10 shadow-lg transition-transform duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] active:scale-[0.97] motion-reduce:transition-none"
		variant="solid"
		size="lg"
		icon-left="lucide-plus"
		label="Create Event"
		:route="{ name: 'create-event' }"
	/>
</template>
