<script setup lang="ts">
import { Avatar, Badge, Tooltip, dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import EventHoverCard from "@/components/dashboard/events/EventHoverCard.vue"
import { enquiryPrice, enquiryStatusTheme } from "@/components/dashboard/sponsorships/helpers"
import { enquiryStatusIcon } from "@/components/dashboard/sponsorships/mine/enquiryStatus"
import type { SponsorshipWithEvent } from "@/types"

const props = defineProps<{ enquiry: SponsorshipWithEvent }>()

const emit = defineEmits<{ open: [] }>()

const price = computed(() => enquiryPrice(props.enquiry))

// creation is a full timestamp in the site's timezone, so this one does convert.
const submitted = computed(() => dayjsLocal(props.enquiry.creation))
</script>

<template>
	<article class="enquiry-card relative rounded-8 border border-outline-gray-2">
		<!-- Overlay rather than a wrapper: the event hover card cannot nest in a button. -->
		<button
			type="button"
			class="absolute inset-0 rounded-8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-3"
			:aria-label="`Open ${enquiry.company_name} enquiry`"
			@click="emit('open')"
		/>

		<div class="flex flex-col space-y-6 p-4">
			<div class="flex items-center gap-3">
				<Avatar
					shape="square"
					size="2xl"
					:image="enquiry.company_logo || undefined"
					:label="enquiry.company_name"
				/>
				<div class="min-w-0 flex-1 space-y-1">
					<h3 class="truncate font-semibold text-xl text-ink-gray-8">
						{{ enquiry.company_name }}
					</h3>
					<p class="text-base text-ink-gray-7">
						For
						<EventHoverCard
							class="text-ink-gray-8"
							:title="enquiry.event_title"
							:start-date="enquiry.start_date"
							:start-time="enquiry.start_time"
							:venue="enquiry.venue"
							:banner-image="enquiry.banner_image"
						/>
					</p>
				</div>
				<div v-if="enquiry.tier" class="shrink-0 space-y-0.5 text-right">
					<p class="text-base font-medium text-ink-gray-8">{{ enquiry.tier_title }}</p>
					<p class="text-sm text-ink-gray-5">{{ price }}</p>
				</div>
			</div>

			<div class="flex justify-between gap-4">
				<Badge class="w-fit" :theme="enquiryStatusTheme(enquiry.status)">
					<template #prefix>
						<span :class="enquiryStatusIcon(enquiry.status)" class="size-3.5" />
					</template>
					<span class="ml-0.5">{{ enquiry.status }}</span>
				</Badge>
				<Tooltip :text="`Submitted on ${submitted.format('D MMM YYYY, h:mm A')}`">
					<span class="flex items-center gap-1 text-ink-gray-5">
						<span class="lucide-clock-fading size-3.5" aria-hidden="true" />
						<span class="shrink-0 text-sm">{{ submitted.fromNow() }}</span>
					</span>
				</Tooltip>
			</div>
		</div>
	</article>
</template>

<style scoped>
.enquiry-card {
	transition:
		transform 120ms cubic-bezier(0.23, 1, 0.32, 1),
		border-color 160ms ease;
}

.enquiry-card:has(> button:active) {
	transform: scale(0.995);
}

/* A touch tap fires hover and leaves it stuck. */
@media (hover: hover) and (pointer: fine) {
	.enquiry-card:hover {
		border-color: var(--outline-gray-3);
	}
}

@media (prefers-reduced-motion: reduce) {
	.enquiry-card:has(> button:active) {
		transform: none;
	}
}
</style>
