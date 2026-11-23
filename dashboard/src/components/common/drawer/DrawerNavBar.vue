<script setup lang="ts">
import { Button, Tooltip } from "frappe-ui"

import DrawerCloseButton from "./DrawerCloseButton.vue"

// The top row of a drawer that steps through a list: close, then whatever names the
// record (default slot), then previous / next and any actions (`actions` slot).
// `noun` names the record in labels, e.g. "guest" gives "Next guest".
defineProps<{ noun: string; hasPrevious: boolean; hasNext: boolean }>()

const emit = defineEmits<{ previous: []; next: [] }>()
</script>

<template>
	<div class="flex items-center gap-2">
		<DrawerCloseButton :label="`Close ${noun}`" />
		<slot />
		<div class="ml-auto flex items-center gap-1">
			<Tooltip :text="`Previous ${noun}`">
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-chevron-up"
					:aria-label="`Previous ${noun}`"
					:disabled="!hasPrevious"
					@click="emit('previous')"
				/>
			</Tooltip>
			<Tooltip :text="`Next ${noun}`">
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-chevron-down"
					:aria-label="`Next ${noun}`"
					:disabled="!hasNext"
					@click="emit('next')"
				/>
			</Tooltip>
			<slot name="actions" />
		</div>
	</div>
</template>
