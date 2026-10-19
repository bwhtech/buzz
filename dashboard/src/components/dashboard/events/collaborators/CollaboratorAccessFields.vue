<script setup lang="ts">
import { Alert, Button, Icon, TabButtons } from "frappe-ui"

import type { SectionLevel } from "@/types"
import {
	describeLevels,
	EVENT_SECTIONS,
	opensAPage,
	type SectionLevels,
	type SectionOption,
	setAllLevels,
} from "@/utils/eventSections"

const levels = defineModel<SectionLevels>({ required: true })

// reka radios cannot carry an empty value, so no access travels as "none".
const LEVEL_TABS = [
	{ label: __("None"), value: "none" },
	{ label: __("View"), value: "View" },
	{ label: __("Edit"), value: "Edit" },
]
const DETAILS_TABS = LEVEL_TABS.slice(1)

function levelOf(section: SectionOption) {
	return levels.value[`${section.key}_access`] || "none"
}

function setLevel(section: SectionOption, value: string | number | undefined) {
	levels.value[`${section.key}_access`] = value === "none" ? "" : (value as SectionLevel)
}
</script>

<template>
	<div class="flex flex-col gap-2">
		<div class="flex min-h-7 items-center justify-between gap-3">
			<span class="text-xs text-ink-gray-5">{{ __("Access by section") }}</span>
			<div class="flex gap-1">
				<Button
					size="sm"
					variant="ghost"
					:label="__('View all')"
					@click="setAllLevels(levels, 'View')"
				/>
				<Button
					size="sm"
					variant="ghost"
					:label="__('Edit all')"
					@click="setAllLevels(levels, 'Edit')"
				/>
			</div>
		</div>

		<div
			v-for="section in EVENT_SECTIONS"
			:key="section.key"
			class="flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-outline-gray-1 py-2"
		>
			<Icon :icon="section.icon" class="size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
			<div class="flex min-w-0 flex-[1_1_10rem] flex-col gap-0.5">
				<span class="text-base text-ink-gray-8">{{ __(section.label) }}</span>
				<span class="text-p-sm text-ink-gray-5">{{ __(section.description) }}</span>
			</div>
			<TabButtons
				class="w-full sm:w-48"
				fluid
				:aria-label="__(section.label)"
				:options="section.key === 'details' ? DETAILS_TABS : LEVEL_TABS"
				:model-value="levelOf(section)"
				@update:model-value="setLevel(section, $event)"
			/>
		</div>

		<!-- Banner layout: a title-only Alert is one fixed-height line and truncates. -->
		<Alert v-if="opensAPage(levels)" class="mt-1" :title="__('What they can do')">
			<template #description>
				<dl class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-2 gap-y-1">
					<template v-for="line in describeLevels(levels)" :key="line.level">
						<dt class="text-ink-gray-5">
							{{ line.level === "Edit" ? __("Can edit:") : __("Can view:") }}
						</dt>
						<dd class="text-pretty">
							{{ line.labels?.map((label) => __(label)).join(", ") ?? __("Every section") }}
						</dd>
					</template>
				</dl>
			</template>
		</Alert>
		<Alert
			v-else
			class="mt-1"
			theme="amber"
			:title="__('Details alone opens no page')"
			:description="__('Give at least one more section.')"
		/>
	</div>
</template>
