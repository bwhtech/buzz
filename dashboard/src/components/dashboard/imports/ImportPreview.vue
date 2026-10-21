<script setup lang="ts">
import { Avatar, Badge } from "frappe-ui"
import { computed } from "vue"

import type { ImportCheck } from "@/components/dashboard/imports/importTypes"

const props = defineProps<{ check: ImportCheck; title: string }>()

// The server sends the first hundred ready rows.
const hiddenRows = computed(() => props.check.ready_rows - props.check.preview.length)
</script>

<template>
	<section class="space-y-3">
		<p class="text-lg font-semibold text-ink-gray-9">{{ title }}</p>
		<ul
			class="max-h-96 divide-y divide-outline-gray-1 overflow-y-auto rounded-4 border border-outline-gray-2"
		>
			<li
				v-for="{ row, values } in check.preview"
				:key="row"
				class="flex items-center gap-3 px-3 py-2.5"
			>
				<Avatar
					class="shrink-0"
					shape="square"
					size="lg"
					:image="values.company_logo ?? undefined"
					:label="values.company_name ?? undefined"
				/>
				<div class="min-w-0 flex-1">
					<p class="truncate text-p-sm font-medium text-ink-gray-9">{{ values.company_name }}</p>
					<p class="truncate text-p-xs text-ink-gray-6">
						{{ [values.website, values.country].filter(Boolean).join(" · ") || "No website" }}
					</p>
				</div>
				<Badge class="shrink-0" :label="values.tier ?? ''" />
			</li>
			<li v-if="hiddenRows > 0" class="px-3 py-2.5 text-p-sm text-ink-gray-5">
				And {{ hiddenRows }} more
			</li>
		</ul>
	</section>
</template>
