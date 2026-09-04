<script setup lang="ts">
import { Avatar, Badge, HoverCard, Tooltip, dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import EventHoverCard from "@/components/dashboard/events/EventHoverCard.vue"
import { useProposalStatuses } from "@/composables/useProposalStatuses"
import { session } from "@/data/session"
import { userResource } from "@/data/user"
import type { ProposalWithEvent } from "@/types"
import { speakerByline } from "@/utils/speakerByline"

// The event line is noise on a page that is already scoped to one event.
const props = withDefaults(defineProps<{ proposal: ProposalWithEvent; showEvent?: boolean }>(), {
	showEvent: true,
})

const emit = defineEmits<{ open: [] }>()

const { getStatusTheme, getStatusIcon } = useProposalStatuses()

const byline = computed(() =>
	speakerByline(props.proposal.speakers, userResource.data?.email || session.user),
)

// modified is a full timestamp in the site's timezone, so this one does convert.
const modified = computed(() => dayjsLocal(props.proposal.modified))
const lastUpdated = computed(() => modified.value.fromNow())
const lastUpdatedExact = computed(() => modified.value.format("D MMM YYYY, h:mm A"))
</script>

<template>
	<article class="proposal-card relative rounded-8 border border-outline-gray-2">
		<!-- Overlay rather than a wrapper: the hover cards inside cannot legally nest in a
		     button. They sit above the overlay, so both targets work and both are focusable. -->
		<button
			type="button"
			class="absolute inset-0 rounded-8 focus-visible:outline focus-visible:outline-2 focus-visible:outline-outline-gray-3"
			:aria-label="`Open ${proposal.title}`"
			@click="emit('open')"
		/>

		<div class="flex flex-col space-y-6 p-4">
			<div class="space-y-2">
				<h3 class="font-semibold text-xl text-ink-gray-8">{{ proposal.title }}</h3>
				<p v-if="byline" class="text-base text-ink-gray-7">
					By {{ byline.lead
					}}<template v-if="byline.rest.length === 1"> &amp; {{ byline.rest[0] }}</template>
					<template v-else-if="byline.rest.length">
						and
						<HoverCard :hover-delay="0.15" align="start">
							<template #trigger>
								<span
									class="relative z-10 underline decoration-dotted underline-offset-2 transition-colors hover:text-ink-gray-9"
								>
									{{ byline.rest.length }} others
								</span>
							</template>
							<div class="p-2">
								<ul class="space-y-2">
									<li
										v-for="(name, index) in byline.rest"
										:key="index"
										class="flex items-center gap-2 text-sm text-ink-gray-8"
									>
										<Avatar size="sm" :label="name" />
										<span class="min-w-0 truncate">{{ name }}</span>
									</li>
								</ul>
							</div>
						</HoverCard>
						<!-- The card is hover-only, so the names need a spoken path too. -->
						<span class="sr-only">: {{ byline.rest.join(", ") }}</span>
					</template>
				</p>
			</div>

			<div class="flex gap-4 justify-between">
				<div class="flex items-center gap-2">
					<Badge class="w-fit" :theme="getStatusTheme(proposal.status)">
						<template #prefix>
							<span :class="getStatusIcon(proposal.status)" class="size-3.5" />
						</template>
						<span class="ml-0.5">{{ proposal.status }}</span>
					</Badge>
					<p v-if="showEvent" class="text-base text-ink-gray-7">
						For
						<EventHoverCard
							class="text-ink-gray-8"
							:event="proposal.event"
							:title="proposal.event_title"
							:start-date="proposal.start_date"
							:start-time="proposal.start_time"
							:venue="proposal.venue"
							:banner-image="proposal.banner_image"
						/>
					</p>
				</div>
				<Tooltip :text="`Last updated on ${lastUpdatedExact}`">
					<span class="flex items-center gap-1 text-ink-gray-5">
						<span class="lucide-clock-fading size-3.5"></span>
						<p class="shrink-0 text-sm">{{ lastUpdated }}</p>
					</span>
				</Tooltip>
			</div>
		</div>
	</article>
</template>

<style scoped>
.proposal-card {
	transition:
		transform 120ms cubic-bezier(0.23, 1, 0.32, 1),
		border-color 160ms ease;
}

/* Only the overlay opens the drawer, so only its press answers back. */
.proposal-card:has(> button:active) {
	transform: scale(0.995);
}

/* A touch tap fires hover and leaves it stuck. */
@media (hover: hover) and (pointer: fine) {
	.proposal-card:hover {
		border-color: var(--outline-gray-3);
	}
}

@media (prefers-reduced-motion: reduce) {
	.proposal-card:has(> button:active) {
		transform: none;
	}
}
</style>
