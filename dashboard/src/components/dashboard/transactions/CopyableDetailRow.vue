<script setup lang="ts">
import { Button } from "frappe-ui"

import DetailRow from "@/components/common/DetailRow.vue"
import { useCopyToClipboard } from "@/composables/useCopyToClipboard"

defineProps<{ label: string; value: string | null }>()

const copyToClipboard = useCopyToClipboard()
</script>

<template>
	<DetailRow :label="label" :value="value">
		<span v-if="value" class="font-mono text-sm" :title="value">{{ value }}</span>
		<span v-else class="text-ink-gray-5">—</span>
		<template v-if="value" #suffix>
			<Button
				variant="ghost"
				size="sm"
				icon="lucide-copy"
				:aria-label="`Copy ${label.toLowerCase()}`"
				@click="copyToClipboard(value, `${label} copied`)"
			/>
		</template>
	</DetailRow>
</template>
