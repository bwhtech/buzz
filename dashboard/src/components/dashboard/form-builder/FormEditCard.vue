<script setup lang="ts">
import { Badge, Button, Skeleton, useDoc } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import type { BuzzFormDoc } from "@/components/dashboard/form-builder/useFormBuilder"

const props = defineProps<{ form: string }>()

const route = useRoute()
const doc = useDoc<BuzzFormDoc>({ doctype: "Buzz Form", name: props.form })

const editRoute = computed(() => ({
	name: "event-form",
	params: { eventId: route.params.eventId as string, formName: props.form },
}))

const TALL_FIELDTYPES = ["Small Text", "Text", "Long Text", "Text Editor", "Markdown Editor"]

const questions = computed(() =>
	(doc.doc?.questions ?? []).filter((question) => question.enabled).slice(0, 4),
)
</script>

<template>
	<!-- The cover is a miniature of the form, so the card reads as this form before the
		 title is read. The button is the one focus stop; its overlay stretches the click
		 target over the whole card. -->
	<div
		v-if="doc.doc"
		class="group relative overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-white transition-[transform,background-color] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] active:scale-[0.98] motion-reduce:transition-none [@media(hover:hover)]:hover:bg-surface-gray-1"
	>
		<div
			class="h-32 overflow-hidden bg-surface-gray-2 px-5 pt-4 [mask-image:linear-gradient(to_bottom,black_65%,transparent)]"
			aria-hidden="true"
		>
			<div
				class="space-y-2 rounded-t-4 border border-b-0 border-outline-gray-2 bg-surface-white p-3 shadow-sm transition-transform duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none [@media(hover:hover)]:group-hover:-translate-y-1"
			>
				<p class="truncate text-xs font-semibold text-ink-gray-9">{{ doc.doc.title }}</p>
				<div v-for="question in questions" :key="question.fieldname" class="space-y-1">
					<p class="truncate text-[10px] text-ink-gray-6">
						{{ question.label }}<span v-if="question.mandatory" class="text-ink-red-4"> *</span>
					</p>
					<div
						class="rounded-2 bg-surface-gray-2"
						:class="TALL_FIELDTYPES.includes(question.fieldtype) ? 'h-7' : 'h-3'"
					/>
				</div>
			</div>
		</div>
		<div class="flex items-center justify-between gap-2 border-t border-outline-gray-1 px-3 py-2.5">
			<div class="min-w-0 space-y-1">
				<p class="truncate text-p-sm font-medium text-ink-gray-9">{{ doc.doc.title }}</p>
				<Badge
					:theme="doc.doc.publish ? 'green' : 'gray'"
					:label="doc.doc.publish ? 'Live' : 'Draft'"
				/>
			</div>
			<Button
				class="shrink-0 after:absolute after:inset-0"
				variant="ghost"
				icon="lucide-pencil"
				label="Edit form"
				tooltip="Edit form"
				:route="editRoute"
			/>
		</div>
	</div>
	<Skeleton v-else-if="doc.loading" class="h-[11.5rem] w-full rounded-5" />
</template>
