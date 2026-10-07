<script setup lang="ts">
import { Button, ErrorMessage, Skeleton } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import AddMembersDialog from "@/components/dashboard/teams/AddMembersDialog.vue"
import TeamMembersTable from "@/components/dashboard/teams/TeamMembersTable.vue"
import TeamPageHeader from "@/components/dashboard/teams/TeamPageHeader.vue"
import TeamRoleGuide from "@/components/dashboard/teams/TeamRoleGuide.vue"
import { reloadTeams, useTeamOverview } from "@/data/teams"
import { serverErrorMessage } from "@/utils/serverError"
import { canManageMembers } from "@/utils/teamRoles"

const route = useRoute()
const teamId = route.params.teamId as string
const overview = useTeamOverview(teamId)

const canManage = computed(() => canManageMembers(overview.data?.my_role))
const isAdding = ref(false)

// The teams list shows member avatars, so it follows every change.
async function refresh() {
	await overview.reload()
	reloadTeams()
}
</script>

<template>
	<TeamPageHeader section="Team Members">
		<Button
			v-if="canManage"
			variant="solid"
			icon-left="lucide-plus"
			:label="__('Add member')"
			@click="isAdding = true"
		/>
	</TeamPageHeader>

	<div class="m-auto flex w-full max-w-[800px] flex-col gap-6 px-4 py-8">
		<TeamRoleGuide />

		<ErrorMessage v-if="overview.error" :message="serverErrorMessage(overview.error)" />

		<TeamMembersTable v-else-if="overview.data" :team="overview.data" @changed="refresh" />

		<ul v-else :aria-label="__('Loading members')">
			<li v-for="row in 3" :key="row" class="flex items-center gap-3 py-2">
				<Skeleton class="size-8 shrink-0 rounded-full" />
				<Skeleton class="h-4 w-36 rounded-4" />
				<Skeleton class="ml-auto h-4 w-16 rounded-4" />
			</li>
		</ul>
	</div>

	<AddMembersDialog v-model="isAdding" :team="teamId" @success="refresh" />
</template>
