<script setup lang="ts">
import { Avatar, Button, ErrorMessage, Skeleton, dayjs, toast } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import EmptyState from "@/components/common/EmptyState.vue"
import SectionHeader from "@/components/common/SectionHeader.vue"
import TeamPageHeader from "@/components/dashboard/teams/TeamPageHeader.vue"
import { useCommunityRequests, useReviewRequest } from "@/data/communities"
import { serverErrorMessage } from "@/utils/serverError"

const route = useRoute()
const requests = useCommunityRequests(route.params.teamId as string)
const approve = useReviewRequest("approve")
const reject = useReviewRequest("reject")
// One call serves every row, so only the row under review shows it loading.
const reviewing = ref<string | null>(null)

const sections = computed(() => [
	{ title: "Pending", rows: requests.data?.pending ?? [], reviewable: true },
	{ title: "Approved", rows: requests.data?.approved ?? [], reviewable: false },
])

async function review(call: typeof approve, request: string, message: string) {
	reviewing.value = request
	await call.submit({ request }).catch(() => null)
	if (call.error) return toast.error(serverErrorMessage(call.error))
	toast.success(__(message))
	requests.reload()
}
</script>

<template>
	<TeamPageHeader section="Community Submissions" />

	<div class="m-auto flex w-full max-w-[800px] flex-col gap-8 px-4 py-8">
		<ErrorMessage v-if="requests.error" :message="serverErrorMessage(requests.error)" />

		<Skeleton v-else-if="!requests.data" class="h-40 w-full rounded-5" />

		<template v-else>
			<section v-for="section in sections" :key="section.title" class="space-y-3">
				<SectionHeader :title="__(section.title)" :count="section.rows.length" />

				<EmptyState
					v-if="!section.rows.length"
					:title="section.reviewable ? __('Nothing to review') : __('No events listed yet')"
				/>

				<ul v-else class="flex flex-col">
					<li
						v-for="request in section.rows"
						:key="request.name"
						class="flex items-center gap-3 border-b border-outline-gray-1 py-3"
					>
						<Avatar
							shape="square"
							size="lg"
							:image="request.event_team_logo ?? undefined"
							:label="request.event_team_name"
						/>
						<div class="flex min-w-0 flex-1 flex-col gap-0.5">
							<span class="truncate text-base font-medium text-ink-gray-8">
								{{ request.event_title }}
							</span>
							<span class="truncate text-sm text-ink-gray-5">
								{{ request.event_team_name }} · {{ dayjs(request.start_date).format("D MMM YYYY") }}
							</span>
						</div>
						<template v-if="section.reviewable">
							<Button
								:label="__('Reject')"
								:loading="reject.loading && reviewing === request.name"
								@click="review(reject, request.name, 'Submission rejected')"
							/>
							<Button
								variant="solid"
								:label="__('Approve')"
								:loading="approve.loading && reviewing === request.name"
								@click="review(approve, request.name, 'Submission approved')"
							/>
						</template>
					</li>
				</ul>
			</section>
		</template>
	</div>
</template>
