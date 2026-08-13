<script setup lang="ts">
import { useProposalStatuses } from "@/composables/useProposalStatuses";
import { session } from "@/data/session";
import { userResource } from "@/data/user";
import type { ProposalWithEvent } from "@/types";
import { bannerPattern } from "@/utils/eventBanner";
import { speakerByline } from "@/utils/speakerByline";
import { Avatar, Badge, HoverCard, dayjs, dayjsLocal } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{ proposal: ProposalWithEvent }>();

const { getStatusTheme } = useProposalStatuses();

const byline = computed(() =>
	speakerByline(props.proposal.speakers, userResource.data?.email || session.user)
);

const banner = computed(() => ({ backgroundImage: bannerPattern(props.proposal.event) }));

// Plain dayjs: start_date is date-only, and a timezone shift moves it a day back.
const eventDate = computed(() => dayjs(props.proposal.start_date).format("D MMM YYYY"));

// modified is a full timestamp in the site's timezone, so this one does convert.
const lastUpdated = computed(() =>
	dayjsLocal(props.proposal.modified).format("D MMM YYYY, h:mm A")
);
</script>

<template>
	<RouterLink
		:to="{ name: 'proposal-details', params: { proposalId: proposal.name } }"
		class="proposal-card block rounded-2xl border border-outline-gray-2"
	>
		<article class="flex flex-col space-y-6 p-4">
			<div class="space-y-2">
				<Badge
					class="w-fit mb-1"
					:label="proposal.status"
					:theme="getStatusTheme(proposal.status)"
				/>
				<h3 class="font-semibold text-xl text-ink-gray-8">{{ proposal.title }}</h3>
				<p v-if="byline" class="text-base text-ink-gray-7">
					By {{ byline.lead
					}}<template v-if="byline.partner"> &amp; {{ byline.partner }}</template>
					<template v-else-if="byline.others.length">
						and
						<HoverCard :hover-delay="0.15" align="start">
							<template #trigger>
								<span
									class="underline decoration-dotted underline-offset-2 transition-colors hover:text-ink-gray-9"
								>
									{{ byline.others.length }} others
								</span>
							</template>
							<div class="p-2">
								<ul class="space-y-2">
									<li
										v-for="(name, index) in byline.others"
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
						<span class="sr-only">: {{ byline.others.join(", ") }}</span>
					</template>
				</p>
			</div>

			<div class="flex gap-4 justify-between">
				<p class="text-base text-ink-gray-7">
					For
					<HoverCard :hover-delay="0.15" align="start">
						<template #trigger>
							<span
								class="font-medium text-ink-gray-8 transition-colors hover:text-ink-gray-9"
								>{{ proposal.event_title }}</span
							>
						</template>
						<div class="w-56 space-y-2 p-2">
							<!-- The pattern also backs the image, so the slot is never blank while it loads. -->
							<img
								v-if="proposal.banner_image"
								class="h-24 w-full rounded object-cover object-top"
								:src="proposal.banner_image"
								:style="banner"
								alt=""
							/>
							<div v-else class="h-24 w-full rounded" :style="banner" />

							<p class="font-medium text-ink-gray-8">{{ proposal.event_title }}</p>
							<p class="text-sm text-ink-gray-5">{{ eventDate }}</p>
						</div>
					</HoverCard>
				</p>
				<p class="shrink-0 text-sm text-ink-gray-6">Last updated {{ lastUpdated }}</p>
			</div>
		</article>
	</RouterLink>
</template>

<style scoped>
.proposal-card {
	transition: transform 160ms cubic-bezier(0.23, 1, 0.32, 1), border-color 160ms ease;
}

.proposal-card:active {
	transform: scale(0.98);
}

/* A touch tap fires hover and leaves it stuck. */
@media (hover: hover) and (pointer: fine) {
	.proposal-card:hover {
		border-color: var(--outline-gray-3);
	}
}

@media (prefers-reduced-motion: reduce) {
	.proposal-card:active {
		transform: none;
	}
}
</style>
