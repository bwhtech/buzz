<script setup lang="ts">
import { Badge, Button, Dropdown, Tooltip } from "frappe-ui"
import { computed } from "vue"

import { eventPageIcon } from "@/components/dashboard/events/pages/eventPageTemplates"
import type { AdditionalEventPage } from "@/types"

const props = defineProps<{
	page: AdditionalEventPage
	published: boolean
	isFirst: boolean
	isLast: boolean
}>()

const emit = defineEmits<{
	togglePublished: []
	duplicate: []
	move: [offset: number]
	delete: []
}>()

function plainText(html: string) {
	return new DOMParser().parseFromString(html || "", "text/html").body.textContent?.trim() ?? ""
}

const excerpt = computed(() => plainText(props.page.content))

const actions = computed(() => [
	{
		group: "",
		hideLabel: true,
		options: [
			{ label: __("Duplicate"), icon: "lucide-copy", onClick: () => emit("duplicate") },
			{
				label: __("Move up"),
				icon: "lucide-arrow-up",
				condition: () => !props.isFirst,
				onClick: () => emit("move", -1),
			},
			{
				label: __("Move down"),
				icon: "lucide-arrow-down",
				condition: () => !props.isLast,
				onClick: () => emit("move", 1),
			},
		],
	},
	{
		group: "",
		hideLabel: true,
		options: [
			{
				label: __("Delete"),
				icon: "lucide-trash-2",
				theme: "red" as const,
				onClick: () => emit("delete"),
			},
		],
	},
])
</script>

<template>
	<!-- The whole row opens the page; the button inside is its keyboard stop. -->
	<div class="flex min-w-0 flex-1 cursor-pointer items-center gap-3">
		<button
			type="button"
			class="flex min-w-0 flex-1 items-center gap-3 rounded-3 text-left transition-opacity focus-visible:outline-none focus-visible:focus-ring"
			:class="{ 'opacity-50': !published }"
			:aria-label="__('Edit {0}', [page.title])"
		>
			<span
				class="grid size-8 shrink-0 place-items-center rounded-3 bg-surface-gray-2 text-ink-gray-6"
			>
				<span :class="[eventPageIcon(page.title), 'size-4']" aria-hidden="true" />
			</span>
			<span class="min-w-0 flex-1">
				<span class="flex items-center gap-2">
					<span class="truncate text-base font-medium text-ink-gray-8">{{ page.title }}</span>
					<Badge v-if="!published" :label="__('Hidden')" size="sm" />
				</span>
				<span class="mt-0.5 block truncate text-sm text-ink-gray-5">
					{{ excerpt || __("Empty — click to write") }}
				</span>
			</span>
		</button>

		<div class="flex items-center gap-0.5" @click.stop>
			<Tooltip :text="published ? __('Hide from event page') : __('Show on event page')">
				<Button
					variant="ghost"
					:icon="published ? 'lucide-eye' : 'lucide-eye-off'"
					:aria-label="published ? __('Hide from event page') : __('Show on event page')"
					@click="emit('togglePublished')"
				/>
			</Tooltip>
			<Dropdown :options="actions" align="end">
				<Button
					variant="ghost"
					icon="lucide-ellipsis"
					:aria-label="__('Actions for {0}', [page.title])"
				/>
			</Dropdown>
		</div>
		<span class="lucide-chevron-right size-4 shrink-0 text-ink-gray-4" aria-hidden="true" />
	</div>
</template>
