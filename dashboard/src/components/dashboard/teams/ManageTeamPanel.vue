<script setup lang="ts">
import {
	Button,
	ErrorMessage,
	FormControl,
	SettingsBody,
	SettingsHeader,
	Skeleton,
	toast,
} from "frappe-ui"
import { computed, reactive, ref, watch } from "vue"

import AvatarUploader from "@/components/common/AvatarUploader.vue"
import AddMembersDialog from "@/components/dashboard/teams/AddMembersDialog.vue"
import TeamMembersTable from "@/components/dashboard/teams/TeamMembersTable.vue"
import { reloadTeams, updateTeam, useTeamOverview } from "@/data/teams"
import { canManageMembers } from "@/utils/teamRoles"

const props = defineProps<{ team: string; teamName: string }>()
defineEmits<{ back: [] }>()

// Plain-language reading of the capability matrix in specs/v2/00-teams.
const ROLES = [
	{ name: "Owner", can: __("Created the team. Full control, and cannot be removed.") },
	{ name: "Admin", can: __("Everything an owner can do, except deleting the team.") },
	{
		name: "Manager",
		can: __("Creates and edits events. Cannot delete records or manage members."),
	},
	{ name: "Frontdesk", can: __("Checks attendees in at the door, and nothing else.") },
	{ name: "Viewer", can: __("Reads the team's events and details. Changes nothing.") },
]

const isAdding = ref(false)

const overview = useTeamOverview(props.team)

const canManage = computed(() => canManageMembers(overview.data?.my_role))

const form = reactive({ team_name: props.teamName, logo: null as string | null })

// The overview arrives after the panel opens, so the form follows it in.
watch(
	() => overview.data,
	(team) => team && Object.assign(form, { team_name: team.team_name, logo: team.logo }),
)

const isDirty = computed(
	() =>
		!!overview.data &&
		(form.team_name !== overview.data.team_name || form.logo !== overview.data.logo),
)

// A logo has no blur: an upload or a remove is the whole gesture.
watch(() => form.logo, save)

const title = computed(() => overview.data?.team_name ?? props.teamName)

async function save() {
	if (!isDirty.value || !form.team_name.trim()) return

	// Rejects on failure; updateTeam.error renders inline, so the rejection is swallowed.
	await updateTeam.submit({ team: props.team, ...form }).catch(() => null)
	if (updateTeam.error) return

	await refresh()
	toast.success(__("Team updated"))
}

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
				<template v-if="canManage">
					<AvatarUploader
						v-model="form.logo"
						shape="square"
						:label="title"
						:title="__('Team logo')"
						:description="__('Shown wherever the team appears')"
					/>

					<FormControl
						type="text"
						class="max-w-sm"
						:label="__('Team Name')"
						v-model="form.team_name"
						@blur="save"
					/>

					<ErrorMessage :message="(updateTeam.error as Error | null)?.message" />
				</template>

				<h3 class="text-base-semibold text-ink-gray-8">{{ __("Team Members") }}</h3>

				<section class="-mt-3 rounded-7 bg-surface-gray-1 p-4">
					<h4 class="text-sm font-medium text-ink-gray-7">{{ __("What each role can do") }}</h4>
					<dl class="mt-3 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
						<div v-for="role in ROLES" :key="role.name" class="flex gap-2">
							<dt class="w-20 shrink-0 font-medium text-ink-gray-7">{{ role.name }}</dt>
							<dd class="text-ink-gray-5">{{ role.can }}</dd>
						</div>
					</dl>
				</section>

				<ErrorMessage v-if="overview.error" :message="overview.error.message" />

				<TeamMembersTable v-else-if="overview.data" :team="overview.data" @removed="refresh" />

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
