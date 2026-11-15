<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed } from "vue"

import { pluralize } from "@/utils/pluralize"

const props = defineProps<{ total: number; pageSize: number }>()
const page = defineModel<number>("page", { required: true })

const pageCount = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

const count = new Intl.NumberFormat()

const range = computed(() => {
	if (props.total <= props.pageSize) return pluralize(props.total, "transaction")
	const start = (page.value - 1) * props.pageSize + 1
	const end = Math.min(props.total, page.value * props.pageSize)
	return `${count.format(start)}–${count.format(end)} of ${count.format(props.total)}`
})
</script>

<template>
	<nav
		aria-label="Pagination"
		class="flex items-center justify-between gap-2 text-sm text-ink-gray-5"
	>
		<span class="tabular-nums" aria-live="polite">{{ range }}</span>
		<div v-if="pageCount > 1" class="flex items-center gap-1">
			<Button
				size="sm"
				variant="ghost"
				icon="lucide-chevron-left"
				aria-label="Previous page"
				:disabled="page <= 1"
				@click="page--"
			/>
			<Button
				size="sm"
				variant="ghost"
				icon="lucide-chevron-right"
				aria-label="Next page"
				:disabled="page >= pageCount"
				@click="page++"
			/>
		</div>
	</nav>
</template>
