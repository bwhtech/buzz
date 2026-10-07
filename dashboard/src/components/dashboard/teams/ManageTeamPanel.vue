<script setup lang="ts">
import { Button, ErrorMessage, SettingsBody, SettingsHeader, Skeleton } from "frappe-ui"
import { computed, ref } from "vue"

import AddMembersDialog from "@/components/dashboard/teams/AddMembersDialog.vue"
import TeamIdentityForm from "@/components/dashboard/teams/TeamIdentityForm.vue"
import TeamMembersTable from "@/components/dashboard/teams/TeamMembersTable.vue"
import TeamPublicPage from "@/components/dashboard/teams/TeamPublicPage.vue"
import TeamRoleGuide from "@/components/dashboard/teams/TeamRoleGuide.vue"
import { reloadTeams, useTeamOverview } from "@/data/teams"
import { serverErrorMessage } from "@/utils/serverError"
import { canEditPublicPage, canManageMembers } from "@/utils/teamRoles"

const props = defineProps<{ team: string; teamName: string }>()
defineEmits<{ back: [] }>()

const isAdding = ref(false)

const overview = useTeamOverview(props.team)

const canManage = computed(() => canManageMembers(overview.data?.my_role))
const canEditPage = computed(() => canEditPublicPage(overview.data?.my_role))

const title = computed(() => overview.data?.team_name ?? props.teamName)

// The teams list behind this view shows member avatars, so it has to follow every change.
async function refresh() {
	await overview.reload()
	reloadTeams()
}
</script>

<template>
	<div class="flex min-h-0 flex-1 flex-col">
		<SettingsHeader>
			<div class="flex items-start justify-between gap-4">
				<div class="flex min-w-0 items-center gap-1">
					<Button variant="ghost" :label="__('Back to teams')" @click="$emit('back')">
						<template #icon>
							<span class="lucide-chevron-left size-4" />
						</template>
					</Button>
					<h2 class="truncate text-lg font-semibold text-ink-gray-8">{{ title }}</h2>
				</div>
				<Button
					v-if="canManage"
					icon-left="lucide-plus"
					:label="__('Add member')"
					@click="isAdding = true"
				/>
			</div>
		</SettingsHeader>

		<SettingsBody>
			<div class="flex flex-col gap-6 pt-6">
				<TeamIdentityForm
					v-if="canManage && overview.data"
					:team="overview.data"
					@saved="refresh"
				/>

				<TeamPublicPage
					v-if="canEditPage && overview.data"
					:team="overview.data"
					@saved="refresh"
				/>

				<h3 class="text-base-semibold text-ink-gray-8">{{ __("Team Members") }}</h3>

				<TeamRoleGuide class="-mt-3" />

				<ErrorMessage v-if="overview.error" :message="serverErrorMessage(overview.error)" />

				<TeamMembersTable v-else-if="overview.data" :team="overview.data" @changed="refresh" />

				<!-- Shaped like a TeamMembersTable row, so members land where the placeholders stood. -->
				<ul v-else :aria-label="__('Loading members')" class="pt-7">
					<li v-for="row in 3" :key="row" class="flex items-center gap-3 py-2">
						<Skeleton class="size-8 shrink-0 rounded-full" />
						<Skeleton class="h-4 w-36 rounded-4" />
						<Skeleton class="ml-auto h-4 w-16 rounded-4" />
					</li>
				</ul>
			</div>
		</SettingsBody>

		<AddMembersDialog v-model="isAdding" :team="team" @success="refresh" />
	</div>
</template>
