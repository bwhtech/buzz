<script setup lang="ts">
import { Button } from "frappe-ui"

defineProps<{ isDirty: boolean; saving: boolean; disabled?: boolean }>()
defineEmits<{ save: []; discard: [] }>()
</script>

<template>
	<Transition
		enter-active-class="transition duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
		enter-from-class="opacity-0 translate-y-1"
		leave-active-class="transition duration-100 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
		leave-to-class="opacity-0"
	>
		<div v-if="isDirty" class="flex items-center gap-2">
			<!-- On a phone Discard takes the back button's place; see TeamPageHeader. -->
			<Button class="max-md:hidden" :label="__('Discard')" @click="$emit('discard')" />
			<Button
				variant="solid"
				:label="__('Save')"
				:disabled="disabled"
				:loading="saving"
				@click="$emit('save')"
			/>
		</div>
	</Transition>
</template>
