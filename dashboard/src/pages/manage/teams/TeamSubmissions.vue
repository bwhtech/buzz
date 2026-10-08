<script setup lang="ts">
import { ErrorMessage, Skeleton } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import EmptyState from "@/components/common/EmptyState.vue"
import SectionHeader from "@/components/common/SectionHeader.vue"
import SubmissionRow from "@/components/dashboard/teams/SubmissionRow.vue"
import TeamPageHeader from "@/components/dashboard/teams/TeamPageHeader.vue"
import { useCommunityQueue } from "@/data/communities"
import { useTeamOverview } from "@/data/teams"
import { serverErrorMessage } from "@/utils/serverError"
import { canEditPublicPage } from "@/utils/teamRoles"

const teamId = useRoute().params.teamId as string
const queue = useCommunityQueue(teamId)
const overview = useTeamOverview(teamId)

const canReview = computed(() => canEditPublicPage(overview.data?.my_role))
const sections = computed(() => [
	{ title: __("Pending"), requests: queue.data?.pending ?? [] },
	{ title: __("Approved"), requests: queue.data?.approved ?? [] },
])
const isEmpty = computed(() => sections.value.every((section) => !section.requests.length))
</script>

<template>
	<TeamPageHeader section="Submissions" />

	<div class="m-auto flex w-full max-w-[800px] flex-col gap-8 p-4 max-md:pb-24">
		<ErrorMessage v-if="queue.error" :message="serverErrorMessage(queue.error)" />

		<ul v-else-if="!queue.data" :aria-label="__('Loading submissions')">
			<li v-for="row in 3" :key="row" class="flex items-center gap-3 py-3">
				<Skeleton class="size-10 shrink-0 rounded-4" />
				<Skeleton class="h-4 w-48 rounded-4" />
				<Skeleton class="ml-auto h-7 w-32 rounded-4" />
			</li>
		</ul>

		<EmptyState
			v-else-if="isEmpty"
			:title="__('No submissions yet')"
			:description="
				__('Events other teams submit to your community will show up here for you to review.')
			"
		/>

		<template v-else>
			<section v-for="section in sections" :key="section.title" class="space-y-2">
				<SectionHeader :title="section.title" :count="section.requests.length" />
				<ul v-if="section.requests.length">
					<SubmissionRow
						v-for="request in section.requests"
						:key="request.name"
						:request="request"
						:can-review="canReview"
						@changed="queue.reload()"
					/>
				</ul>
				<p v-else class="py-3 text-base text-ink-gray-5">{{ __("Nothing here") }}</p>
			</section>
		</template>
	</div>
</template>
