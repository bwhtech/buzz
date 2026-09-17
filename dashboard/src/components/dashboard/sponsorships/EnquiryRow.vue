<script setup lang="ts">
import { Avatar, Badge, Icon, Tooltip, dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import {
	enquiryStatusTheme,
	shortSubmittedAt,
	websiteLabel,
} from "@/components/dashboard/sponsorships/helpers"
import type { EventEnquiryItem } from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"

const props = defineProps<{ enquiry: EventEnquiryItem }>()
defineEmits<{ open: [] }>()

const price = computed(() =>
	props.enquiry.tier_price == null
		? null
		: formatWholePriceOrFree(props.enquiry.tier_price, props.enquiry.tier_currency || "INR"),
)
const submittedExact = computed(() =>
	dayjsLocal(props.enquiry.creation).format("D MMM YYYY, h:mm A"),
)
</script>

<template>
	<li>
		<button
			type="button"
			class="flex w-full items-center gap-4 rounded-4 border border-outline-gray-2 p-3 text-left transition-colors hover:bg-surface-gray-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
			@click="$emit('open')"
		>
			<Avatar
				shape="square"
				size="xl"
				:image="enquiry.company_logo || undefined"
				:label="enquiry.company_name"
			/>

			<span class="min-w-0 flex-1 space-y-0.5">
				<span class="block truncate text-base font-medium text-ink-gray-8">
					{{ enquiry.company_name }}
				</span>
				<span v-if="enquiry.website" class="block truncate text-sm text-ink-gray-5">
					{{ websiteLabel(enquiry.website) }}
				</span>
			</span>

			<span v-if="enquiry.tier" class="hidden shrink-0 space-y-0.5 text-right sm:block">
				<span class="block text-base font-medium text-ink-gray-8">{{ price }}</span>
				<span class="block text-sm text-ink-gray-5">{{ enquiry.tier_title }}</span>
			</span>

			<span class="flex w-32 shrink-0 justify-end">
				<Badge size="md" :theme="enquiryStatusTheme(enquiry.status)" :label="enquiry.status" />
			</span>

			<Tooltip :text="`Submitted on ${submittedExact}`">
				<span class="hidden w-20 shrink-0 text-right text-sm text-ink-gray-5 sm:block">
					{{ shortSubmittedAt(enquiry.creation) }}
				</span>
			</Tooltip>

			<Icon name="lucide-chevron-right" class="size-4 shrink-0 text-ink-gray-4" />
		</button>
	</li>
</template>
