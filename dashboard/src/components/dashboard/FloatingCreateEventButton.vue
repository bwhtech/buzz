<script setup lang="ts">
import { Button } from "frappe-ui"
</script>

<template>
	<Button
		class="fixed bottom-20 right-4 z-10 shadow-lg"
		variant="solid"
		size="lg"
		icon-left="lucide-plus"
		label="Create Event"
		:route="{ name: 'create-event' }"
	/>
</template>
