<script setup lang="ts">
import { FormControl, Icon, Select } from "frappe-ui"

import type { RequestSort } from "@/utils/requestQueue"

defineProps<{ searchPlaceholder: string; ticketTypes: string[] }>()
const search = defineModel<string>("search", { required: true })
const sort = defineModel<RequestSort>("sort", { required: true })
const ticketType = defineModel<string>("ticketType", { required: true })

const SORT_OPTIONS = [
	{ value: "newest", label: "Newest first" },
	{ value: "oldest", label: "Oldest first" },
	{ value: "name", label: "Name" },
]
</script>

<template>
	<div class="flex flex-wrap items-end gap-2">
		<FormControl
			v-model="search"
			class="min-w-48 flex-1"
			size="sm"
			type="text"
			:placeholder="searchPlaceholder"
			:aria-label="searchPlaceholder"
		>
			<template #prefix>
				<Icon icon="lucide-search" class="size-4 text-ink-gray-5" />
			</template>
		</FormControl>
		<Select
			v-if="ticketTypes.length > 1"
			v-model="ticketType"
			size="sm"
			aria-label="Ticket type"
			:options="[
				{ value: '', label: 'All ticket types' },
				...ticketTypes.map((value) => ({ value, label: value })),
			]"
		/>
		<Select v-model="sort" size="sm" aria-label="Sort by" :options="SORT_OPTIONS" />
	</div>
</template>
