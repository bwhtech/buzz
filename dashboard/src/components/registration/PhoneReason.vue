<template>
	<Popover v-model:open="open" trigger="manual" :auto-focus="false" :offset="6">
		<template #trigger>
			<button
				type="button"
				class="w-fit text-p-sm text-ink-gray-5 underline decoration-dotted underline-offset-2 hover:text-ink-gray-8 focus-visible:text-ink-gray-8"
				@mouseenter="open = true"
				@mouseleave="open = false"
				@focus="open = true"
				@blur="open = false"
			>
				{{ __("Why do we need this?") }}
			</button>
		</template>
		<p class="max-w-64 px-3 py-2 text-p-sm text-ink-gray-7 text-pretty">
			{{
				__(
					"Your payment provider needs a phone number to process the payment. We use it for this purpose only, never for marketing.",
				)
			}}
		</p>
	</Popover>
</template>

<script setup lang="ts">
import { Popover } from "frappe-ui"
import { ref } from "vue"

const open = ref(false)
</script>
