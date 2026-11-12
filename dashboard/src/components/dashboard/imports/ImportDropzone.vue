<script setup lang="ts">
import { Button } from "frappe-ui"

defineProps<{
	// What the sheet must hold, shown beside the template download.
	requirement: string
	rowLimit: number
	// Upload progress in percent while a file is on its way.
	progress?: number | null
	// Whether the caller listens for rows pasted from a spreadsheet.
	acceptsPaste?: boolean
}>()

const emit = defineEmits<{ file: [file: File]; template: [] }>()

const pick = (file: File | null | undefined) => file && emit("file", file)
</script>

<template>
	<div class="space-y-3">
		<label
			class="flex cursor-pointer flex-col items-center gap-2 rounded-7 border border-dashed border-outline-gray-3 bg-surface-gray-1 px-5 py-9 text-center focus-within:focus-ring"
			@dragover.prevent
			@drop.prevent="pick($event.dataTransfer?.files[0])"
		>
			<span class="lucide-upload size-5 text-ink-gray-6" aria-hidden="true" />
			<span class="text-p-base font-medium text-ink-gray-9">
				{{ progress != null ? `Uploading ${progress}%` : "Drop a CSV or Excel file" }}
			</span>
			<span class="text-p-sm text-ink-gray-6">
				or click to browse · up to {{ rowLimit.toLocaleString() }} rows
			</span>
			<input
				type="file"
				class="sr-only"
				accept=".csv,.xlsx,.tsv,.txt"
				@change="pick(($event.target as HTMLInputElement).files?.[0])"
			/>
		</label>
		<p v-if="acceptsPaste" class="text-p-sm text-ink-gray-6">
			You can also paste rows copied from Google Sheets or Excel.
		</p>
		<div class="flex flex-wrap items-center justify-between gap-2 text-p-sm text-ink-gray-6">
			<span>{{ requirement }}</span>
			<Button
				variant="ghost"
				size="sm"
				icon-left="lucide-download"
				label="Template"
				@click="emit('template')"
			/>
		</div>
	</div>
</template>
