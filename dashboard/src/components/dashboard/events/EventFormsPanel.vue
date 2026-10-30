<script setup lang="ts">
import { Badge, Button, useList } from "frappe-ui"

import EmptyState from "@/components/common/EmptyState.vue"
import { FORM_SECTIONS } from "@/components/dashboard/form-builder/useFormBuilder"

const props = defineProps<{ event: string }>()

// Registrations, Talks and Sponsorships open their own forms; the rest are listed here.

const forms = useList<{ name: string; title: string; form_doctype: string; publish: 0 | 1 }>({
	doctype: "Buzz Form",
	filters: { event: props.event, form_doctype: ["not in", Object.keys(FORM_SECTIONS)] },
	fields: ["name", "title", "form_doctype", "publish"],
	orderBy: "creation asc",
	limit: 100,
})
</script>

<template>
	<section class="space-y-3">
		<h2 class="text-lg font-semibold text-ink-gray-9">Forms</h2>
		<div class="overflow-hidden rounded-6 border border-outline-gray-2">
			<div v-if="forms.data?.length" class="divide-y divide-outline-gray-1">
				<div
					v-for="form in forms.data"
					:key="form.name"
					class="flex items-center justify-between gap-3 p-4"
				>
					<div class="min-w-0 space-y-1">
						<p class="truncate text-p-base font-medium text-ink-gray-9">{{ form.title }}</p>
						<p class="text-p-sm text-ink-gray-5">{{ form.form_doctype }}</p>
					</div>
					<div class="flex shrink-0 items-center gap-2">
						<Badge
							:label="form.publish ? 'Published' : 'Not published'"
							:theme="form.publish ? 'green' : 'gray'"
						/>
						<Button
							label="Edit"
							:route="{ name: 'event-form', params: { eventId: event, formName: form.name } }"
						/>
					</div>
				</div>
			</div>
			<EmptyState
				v-else-if="forms.data"
				title="No other forms"
				description="Feedback and custom forms of this event show up here."
				icon="lucide-clipboard-list"
			/>
		</div>
	</section>
</template>
