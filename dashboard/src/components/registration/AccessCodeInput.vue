<template>
	<div v-if="!applied" class="flex flex-col gap-2">
		<button
			type="button"
			class="self-start text-p-sm text-ink-gray-6 underline underline-offset-2 transition-colors duration-150 hover:text-ink-gray-9"
			:aria-expanded="open"
			@click="open = !open"
		>
			{{ __("Have an access code?") }}
		</button>
		<div v-if="open" class="flex flex-col gap-1.5">
			<div class="flex items-start gap-1.5">
				<FormControl
					v-model="code"
					class="flex-1 [&_input]:uppercase"
					size="sm"
					:placeholder="__('Enter access code')"
					:aria-label="__('Access code')"
					@keydown.enter.prevent="emit('apply')"
				/>
				<Button variant="outline" size="sm" :loading="loading" @click="emit('apply')">
					{{ __("Apply") }}
				</Button>
			</div>
			<ErrorMessage :message="error" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, ErrorMessage, FormControl } from "frappe-ui"
import { ref } from "vue"

defineProps<{ applied: boolean; error: string; loading: boolean }>()
const emit = defineEmits<{ apply: [] }>()

const code = defineModel<string>({ required: true })
const open = ref(false)
</script>
