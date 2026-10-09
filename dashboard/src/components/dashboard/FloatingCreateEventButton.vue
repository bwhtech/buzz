<script setup lang="ts">
import { Button } from "frappe-ui"

// As a menu trigger it opens the menu around it instead of the create page.
defineProps<{ menuTrigger?: boolean }>()
</script>

<template>
	<!-- A full-width row, so a menu matching the trigger's width spans the screen.
	     Only the button takes taps; z-20 keeps it above list rows whose actions sit at z-10. -->
	<div class="pointer-events-none fixed inset-x-4 bottom-20 z-20 flex justify-end">
		<Button
			class="pointer-events-auto shadow-lg transition-transform duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] active:scale-[0.97] motion-reduce:transition-none"
			variant="solid"
			size="lg"
			icon-left="lucide-plus"
			:label="menuTrigger ? __('Add Event') : __('Create Event')"
			:route="menuTrigger ? undefined : { name: 'create-event' }"
		/>
	</div>
</template>
