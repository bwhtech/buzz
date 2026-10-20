<script setup lang="ts">
import { Button, FormControl } from "frappe-ui"
import { computed } from "vue"

import type { ImportIssue } from "@/components/dashboard/imports/importTypes"

const props = defineProps<{ issue: ImportIssue }>()
const emit = defineEmits<{ choose: [choice: string | null] }>()

const resolved = computed(() => props.issue.choice !== null)

const rows = (count: number) => `${count} ${count === 1 ? "row" : "rows"}`

const title = computed(() => {
	const { kind, column, label, value, count } = props.issue
	if (kind === "column") return `Column “${column}” isn’t matched`
	if (kind === "missing") return `No column holds ${label}`
	if (kind === "value") return `${label} “${value}” doesn’t match anything here (${rows(count)})`
	return resolved.value ? `${rows(count)} skipped` : `${rows(count)} can’t be imported`
})

const detail = computed(() => {
	const { kind, suggestion } = props.issue
	// A column the user has answered for is no longer reported, so this one is still open.
	if (kind === "column") {
		return suggestion
			? `Looks like ${suggestion.label}.`
			: "Pick a field under Columns, or leave it out."
	}
	if (kind === "missing") return "Match a column to it under Columns."
	if (kind === "value") return "Pick what it stands for."
	const shown = props.issue.rows.slice(0, 3).map((row) => `Row ${row.row}: ${row.reason}`)
	return shown.join(" · ") + (props.issue.count > 3 ? ` · and ${props.issue.count - 3} more` : "")
})

const valueChoice = computed({
	get: () => props.issue.choice ?? "",
	set: (choice: string) => emit("choose", choice || null),
})

const valueOptions = computed(() => [
	{ label: "Choose…", value: "" },
	...props.issue.options.map((option) => ({ label: option.label, value: option.value })),
])
</script>

<template>
	<div
		class="flex flex-col gap-2 rounded-4 border p-3"
		:class="resolved ? 'border-outline-gray-2' : 'border-outline-amber-1 bg-surface-amber-1'"
	>
		<div class="flex items-start gap-2.5">
			<span
				class="mt-0.5 size-4 shrink-0"
				:class="
					resolved
						? 'lucide-circle-check text-ink-green-6'
						: 'lucide-triangle-alert text-ink-amber-6'
				"
				aria-hidden="true"
			/>
			<div class="min-w-0 flex-1 space-y-0.5">
				<p class="text-p-sm font-medium text-ink-gray-9">{{ title }}</p>
				<p class="text-p-sm text-ink-gray-6">{{ detail }}</p>
			</div>

			<template v-if="issue.kind === 'column'">
				<Button size="sm" variant="ghost" label="Don’t import" @click="emit('choose', '')" />
				<Button
					v-if="issue.suggestion"
					size="sm"
					variant="solid"
					:label="`Use as ${issue.suggestion.label}`"
					@click="emit('choose', issue.suggestion.value)"
				/>
			</template>

			<Button
				v-else-if="issue.kind === 'rows'"
				size="sm"
				:variant="resolved ? 'ghost' : 'outline'"
				:label="resolved ? 'Undo' : 'Skip them'"
				@click="emit('choose', resolved ? null : 'skip')"
			/>
		</div>

		<FormControl
			v-if="issue.kind === 'value'"
			v-model="valueChoice"
			class="pl-6"
			type="select"
			size="sm"
			:aria-label="`${issue.label} for ${issue.value}`"
			:options="valueOptions"
		/>
	</div>
</template>
