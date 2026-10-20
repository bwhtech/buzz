<script setup lang="ts">
import { useEventListener } from "@vueuse/core"
import {
	Button,
	Checkbox,
	Dialog,
	ErrorMessage,
	FormControl,
	Skeleton,
	useCall,
	useFileUpload,
} from "frappe-ui"
import { computed, reactive, ref, watch } from "vue"

import ImportIssueCard from "@/components/dashboard/imports/ImportIssueCard.vue"
import ImportStatusCard from "@/components/dashboard/imports/ImportStatusCard.vue"
import {
	IMPORTS,
	type ImportCheck,
	type ImportIssue,
	type ImportType,
} from "@/components/dashboard/imports/importTypes"
import type { FrappeError } from "@/types"
import { downloadCsv } from "@/utils/csv"

const props = defineProps<{ event: string; type: ImportType }>()
const open = defineModel<boolean>({ required: true })
const emit = defineEmits<{ imported: [] }>()

const config = computed(() => IMPORTS[props.type])

type Source = { file_url?: string; text?: string; name: string }
type Choices = {
	columns: Record<string, string>
	values: Record<string, Record<string, string>>
	skip_invalid: boolean
	date?: string
}

const source = ref<Source | null>(null)
const choices = reactive<Choices>({ columns: {}, values: {}, skip_invalid: false })
const sendEmails = ref(false)
const showColumns = ref(false)
const status = ref<InstanceType<typeof ImportStatusCard> | null>(null)
const uploader = useFileUpload()

const params = () => ({
	event: props.event,
	import_type: props.type,
	file_url: source.value?.file_url,
	text: source.value?.text,
	choices: JSON.stringify(choices),
})

const checkCall = useCall<ImportCheck, ReturnType<typeof params>>({
	url: "/api/v2/method/buzz.api.imports.check_import",
	method: "POST",
	immediate: false,
})
const startCall = useCall<null, ReturnType<typeof params> & { send_emails: boolean }>({
	url: "/api/v2/method/buzz.api.imports.start_import",
	method: "POST",
	immediate: false,
})

// Every answer is checked again on the server, so the step always shows what an import would do.
watch(choices, () => source.value && checkCall.submit(params()), { deep: true })

const check = computed(() => (source.value ? checkCall.data : null))
const openIssues = computed(
	() =>
		check.value?.issues.filter((issue) => issue.kind === "missing" || issue.choice === null)
			.length ?? 0,
)
const matchedColumns = computed(
	() => check.value?.columns.filter((column) => column.field).length ?? 0,
)
const fieldOptions = computed(() => [
	{ label: "Don’t import", value: "" },
	...(check.value?.fields ?? []).map((field) => ({ label: field.label, value: field.value })),
])
const dayOptions = computed(() =>
	(check.value?.days ?? []).map((day) => ({ label: day.label, value: day.value })),
)
const count = (n: number) => `${n} ${n === 1 ? config.value.one : config.value.noun}`
const message = (error: unknown) => (error as FrappeError | null)?.message

function useSource(next: Source) {
	source.value = next
	// New objects, so the deep watcher sends the check once for the new file.
	choices.columns = {}
	choices.values = {}
	choices.skip_invalid = false
	delete choices.date
}

async function addFile(file: File | undefined) {
	if (!file) return
	const uploaded = await uploader.upload(file, { private: true }).catch(() => null)
	if (uploaded) useSource({ file_url: uploaded.file_url, name: file.name })
}

// Cells copied out of Google Sheets or Excel paste as tab-separated text.
useEventListener(document, "paste", (event: ClipboardEvent) => {
	const text = event.clipboardData?.getData("text/plain")
	if (open.value && !source.value && text?.includes("\n")) useSource({ text, name: "Pasted rows" })
})

function choose(issue: ImportIssue, choice: string | null) {
	if (issue.kind === "rows") choices.skip_invalid = choice !== null
	if (issue.kind === "column" && choice !== null) choices.columns[issue.column!] = choice
	if (issue.kind === "value") {
		const answers = { ...choices.values[issue.field!] }
		if (choice === null) delete answers[issue.value!]
		else answers[issue.value!] = choice
		choices.values[issue.field!] = answers
	}
}

const columnChoice = (column: string, field: string | null) =>
	choices.columns[column] ?? field ?? ""

const downloadTemplate = () =>
	downloadCsv(`${config.value.noun} template.csv`, [config.value.columns])

async function start() {
	await startCall.submit({ ...params(), send_emails: sendEmails.value }).catch(() => null)
	if (startCall.error) return
	status.value?.start()
	open.value = false
}
</script>

<template>
	<Dialog v-model="open" :title="config.title" size="xl" @after-leave="source = null">
		<div v-if="!source" class="space-y-3">
			<p class="text-p-base text-ink-gray-6">{{ config.intro }}</p>
			<label
				class="flex cursor-pointer flex-col items-center gap-2 rounded-7 border border-dashed border-outline-gray-3 bg-surface-gray-1 px-5 py-9 text-center focus-within:focus-ring"
				@dragover.prevent
				@drop.prevent="addFile($event.dataTransfer?.files[0])"
			>
				<span class="lucide-upload size-5 text-ink-gray-6" aria-hidden="true" />
				<span class="text-p-base font-medium text-ink-gray-9">
					{{
						uploader.isUploading.value
							? `Uploading ${uploader.progress.value}%`
							: "Drop a CSV or Excel file"
					}}
				</span>
				<span class="text-p-sm text-ink-gray-6">or click to browse · up to 5,000 rows</span>
				<input
					type="file"
					class="sr-only"
					accept=".csv,.xlsx,.tsv,.txt"
					@change="addFile(($event.target as HTMLInputElement).files?.[0])"
				/>
			</label>
			<p class="text-p-sm text-ink-gray-6">
				You can also paste rows copied from Google Sheets or Excel.
			</p>
			<div class="flex flex-wrap items-center justify-between gap-2 text-p-sm text-ink-gray-6">
				<span>Needs {{ config.needs }}. Everything else is optional.</span>
				<Button
					variant="ghost"
					size="sm"
					icon-left="lucide-download"
					label="Template"
					@click="downloadTemplate"
				/>
			</div>
			<ErrorMessage :message="uploader.error.value?.message" />
		</div>

		<div v-else class="space-y-4">
			<div class="flex items-center gap-2 text-p-sm text-ink-gray-6">
				<span class="lucide-file-spreadsheet size-4 text-ink-green-6" aria-hidden="true" />
				<span class="truncate font-medium text-ink-gray-9">{{ source.name }}</span>
				<span v-if="check">· {{ check.total_rows }} rows</span>
				<Button variant="ghost" size="sm" label="Replace" @click="source = null" />
			</div>

			<ErrorMessage :message="message(checkCall.error)" />
			<Skeleton v-if="!check && !checkCall.error" class="h-24 w-full" />

			<template v-if="check">
				<p class="text-lg font-semibold text-ink-gray-9">
					{{
						openIssues
							? `${openIssues} ${openIssues === 1 ? "thing" : "things"} to sort out`
							: `${count(check.ready_rows)} ready to import`
					}}
				</p>

				<FormControl
					v-if="dayOptions.length > 1"
					v-model="choices.date"
					type="select"
					label="Check-in day"
					description="Your file has no date column."
					:options="dayOptions"
				/>

				<div v-if="check.issues.length" class="space-y-2">
					<ImportIssueCard
						v-for="issue in check.issues"
						:key="`${issue.kind}-${issue.column ?? issue.field}-${issue.value ?? issue.label}`"
						:issue="issue"
						@choose="choose(issue, $event)"
					/>
				</div>

				<ul v-if="check.notes.length" class="space-y-1">
					<li v-for="note in check.notes" :key="note" class="flex gap-2 text-p-sm text-ink-gray-6">
						<span class="lucide-info mt-0.5 size-3.5 shrink-0 text-ink-gray-5" aria-hidden="true" />
						{{ note }}
					</li>
				</ul>

				<div class="border-t border-outline-gray-1 pt-3">
					<Button
						variant="ghost"
						size="sm"
						:icon-left="showColumns ? 'lucide-chevron-down' : 'lucide-chevron-right'"
						:label="`${matchedColumns} of ${check.columns.length} columns matched`"
						:aria-expanded="showColumns"
						@click="showColumns = !showColumns"
					/>
					<div v-if="showColumns" class="mt-2 grid gap-2 sm:grid-cols-2">
						<FormControl
							v-for="column in check.columns"
							:key="column.column"
							type="select"
							size="sm"
							:label="column.column"
							:model-value="columnChoice(column.column, column.field)"
							:options="fieldOptions"
							@update:model-value="choices.columns[column.column] = $event"
						/>
					</div>
				</div>
			</template>
		</div>

		<template v-if="source" #actions>
			<div class="flex flex-wrap items-center justify-end gap-3">
				<Checkbox
					v-if="config.emailLabel"
					v-model="sendEmails"
					class="me-auto"
					:label="config.emailLabel"
				/>
				<Button variant="ghost" label="Cancel" @click="open = false" />
				<Button
					variant="solid"
					:label="`Import ${count(check?.ready_rows ?? 0)}`"
					:disabled="!check?.ready || !check.ready_rows"
					:loading="startCall.loading"
					@click="start"
				/>
			</div>
			<ErrorMessage class="mt-2" :message="message(startCall.error)" />
		</template>
	</Dialog>

	<ImportStatusCard ref="status" :event="event" :type="type" @imported="emit('imported')" />
</template>
