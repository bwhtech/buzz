<script setup lang="ts">
import { Button, FormControl } from "frappe-ui"

import {
	DETAILS_LEVEL_OPTIONS,
	EVENT_SECTIONS,
	LEVEL_OPTIONS,
	type SectionLevels,
	setAllLevels,
} from "@/utils/eventSections"

const levels = defineModel<SectionLevels>({ required: true })
</script>

<template>
	<div class="space-y-3">
		<div class="flex items-center justify-between gap-2">
			<span class="text-sm font-medium text-ink-gray-7">{{ __("Access") }}</span>
			<div class="flex gap-2">
				<Button
					size="sm"
					variant="subtle"
					:label="__('View all')"
					@click="setAllLevels(levels, 'View')"
				/>
				<Button
					size="sm"
					variant="subtle"
					:label="__('Edit all')"
					@click="setAllLevels(levels, 'Edit')"
				/>
			</div>
		</div>

		<div
			v-for="section in EVENT_SECTIONS"
			:key="section.key"
			class="grid grid-cols-[minmax(0,1fr)_8rem] items-center gap-3"
		>
			<div>
				<p class="text-base text-ink-gray-8">{{ __(section.label) }}</p>
				<p class="text-p-sm text-ink-gray-5">{{ __(section.description) }}</p>
			</div>
			<FormControl
				v-model="levels[`${section.key}_access`]"
				type="select"
				:aria-label="__(section.label)"
				:options="section.key === 'details' ? DETAILS_LEVEL_OPTIONS : LEVEL_OPTIONS"
			/>
		</div>
	</div>
</template>
