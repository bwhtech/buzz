<script setup lang="ts">
import { Avatar, ErrorMessage, Skeleton } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import TeamIdentityForm from "@/components/dashboard/teams/TeamIdentityForm.vue"
import TeamPageHeader from "@/components/dashboard/teams/TeamPageHeader.vue"
import TeamPublicPage from "@/components/dashboard/teams/TeamPublicPage.vue"
import { reloadTeams, useTeamOverview } from "@/data/teams"
import { serverErrorMessage } from "@/utils/serverError"
import { canEditPublicPage, canManageMembers } from "@/utils/teamRoles"

const route = useRoute()
const overview = useTeamOverview(route.params.teamId as string)

const canManage = computed(() => canManageMembers(overview.data?.my_role))
const canEditPage = computed(() => canEditPublicPage(overview.data?.my_role))

// The sidebar and the teams list read the name and logo from the teams list.
async function refresh() {
	await overview.reload()
	reloadTeams()
}
</script>

<template>
	<TeamPageHeader section="Details" />

	<div class="m-auto flex w-full max-w-[800px] flex-col gap-6 px-4 py-8">
		<ErrorMessage v-if="overview.error" :message="serverErrorMessage(overview.error)" />

		<Skeleton v-else-if="!overview.data" class="h-40 w-full rounded-5" />

		<template v-else>
			<TeamIdentityForm v-if="canManage" :team="overview.data" @saved="refresh" />

			<div v-else class="flex items-center gap-3">
				<Avatar
					shape="square"
					size="3xl"
					:image="overview.data.logo ?? undefined"
					:label="overview.data.team_name"
				/>
				<h2 class="text-xl font-semibold text-ink-gray-9">{{ overview.data.team_name }}</h2>
			</div>

			<TeamPublicPage v-if="canEditPage" :team="overview.data" @saved="refresh" />
		</template>
	</div>
</template>
