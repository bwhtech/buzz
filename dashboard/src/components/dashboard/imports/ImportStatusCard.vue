<script setup lang="ts">
import { Button, Progress } from "frappe-ui"
import { computed, onBeforeUnmount, ref } from "vue"

import {
	IMPORTS,
	type ImportDone,
	type ImportType,
} from "@/components/dashboard/imports/importTypes"
import { useSocket } from "@/socket"
import { downloadCsv } from "@/utils/csv"

const props = defineProps<{ event: string; type: ImportType }>()
const emit = defineEmits<{ imported: [] }>()

const noun = computed(() => IMPORTS[props.type].noun)
const state = ref<"idle" | "running" | "done">("idle")
const progress = ref({ done: 0, total: 0 })
const result = ref<ImportDone | null>(null)

const percent = computed(() =>
	progress.value.total ? Math.round((progress.value.done / progress.value.total) * 100) : 0,
)
const failed = computed(() => result.value?.failed ?? [])

const title = computed(() => {
	if (state.value === "running") {
		const { done, total } = progress.value
		return `Importing ${noun.value}${total ? ` · ${done} of ${total}` : ""}`
	}
	return result.value?.error
		? "Import failed"
		: `${result.value?.imported} ${result.value?.imported === 1 ? IMPORTS[props.type].one : noun.value} imported`
})

function start() {
	progress.value = { done: 0, total: 0 }
	result.value = null
	state.value = "running"
}

// Every import on the site reaches this user's socket; only this page's kind is ours.
const ours = (message: ImportDone) =>
	String(message.event) === String(props.event) && message.import_type === noun.value

const onProgress = (message: ImportDone & { done: number; total: number }) => {
	if (ours(message)) progress.value = { done: message.done, total: message.total }
}
const onDone = (message: ImportDone) => {
	if (!ours(message)) return
	result.value = message
	state.value = "done"
	emit("imported")
}

const socket = useSocket()
socket?.on("buzz_import_progress", onProgress)
socket?.on("buzz_import_done", onDone)
onBeforeUnmount(() => {
	socket?.off("buzz_import_progress", onProgress)
	socket?.off("buzz_import_done", onDone)
})

function downloadFailedRows() {
	const { header = [], failed_cells = [] } = result.value ?? {}
	downloadCsv(`${noun.value} failed rows.csv`, [
		[...header, "Reason"],
		...failed_cells.map((cells, index) => [...cells, failed.value[index]?.reason]),
	])
}

defineExpose({ start })
</script>

<template>
	<Teleport to="body">
		<div
			v-if="state !== 'idle'"
			role="status"
			aria-live="polite"
			class="fixed right-4 bottom-4 z-50 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2.5 rounded-7 bg-surface-modal p-4 shadow-xl ring-1 ring-outline-gray-1"
		>
			<div class="flex items-center gap-2">
				<span
					class="size-4 shrink-0"
					:class="{
						'lucide-loader-circle animate-spin text-ink-gray-6': state === 'running',
						'lucide-circle-check text-ink-green-6': state === 'done' && !result?.error,
						'lucide-circle-x text-ink-red-6': result?.error,
					}"
					aria-hidden="true"
				/>
				<p class="flex-1 text-p-sm font-medium text-ink-gray-9">{{ title }}</p>
				<Button
					v-if="state === 'done'"
					size="sm"
					variant="ghost"
					icon="lucide-x"
					aria-label="Dismiss"
					@click="state = 'idle'"
				/>
			</div>

			<template v-if="state === 'running'">
				<Progress :value="percent" size="sm" aria-label="Import progress" />
				<p class="text-p-xs text-ink-gray-6">
					You can keep working. This card updates when it’s done.
				</p>
			</template>

			<template v-else>
				<p v-if="result?.error" class="text-p-xs text-ink-gray-6">{{ result.error }}</p>
				<p v-if="failed.length" class="text-p-xs text-ink-gray-6">
					{{ failed.length === 1 ? "1 row" : `${failed.length} rows` }} failed.
					{{ failed[0].reason }}
				</p>
				<p v-for="note in result?.notes ?? []" :key="note" class="text-p-xs text-ink-gray-6">
					{{ note }}
				</p>
				<Button
					v-if="failed.length"
					class="self-start"
					size="sm"
					icon-left="lucide-download"
					label="Download failed rows"
					@click="downloadFailedRows"
				/>
			</template>
		</div>
	</Teleport>
</template>
