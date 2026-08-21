<script setup lang="ts">
import AddMembersDialog from "@/components/dashboard/teams/AddMembersDialog.vue";
import TeamPageHeader from "@/components/dashboard/teams/TeamPageHeader.vue";
import { session } from "@/data/session";
import { currentTeam, removeMember, teamOverviewError, useTeamOverview } from "@/data/teams";
import type { TeamInvite, TeamMember } from "@/types";
import { Avatar, Button, Dropdown, ErrorMessage, LoadingText, dialog, toast } from "frappe-ui";
import { computed, ref } from "vue";

const MANAGING_ROLES = ["Owner", "Admin"];

// Plain-language reading of the capability matrix in specs/v2/00-teams.
const ROLES = [
	{ name: "Owner", can: "Created the team. Full control, and cannot be removed." },
	{ name: "Admin", can: "Everything an owner can do, except renaming or deleting the team." },
	{ name: "Manager", can: "Creates and edits events. Cannot delete records or manage members." },
	{ name: "Frontdesk", can: "Checks attendees in at the door, and nothing else." },
	{ name: "Viewer", can: "Reads the team's events and details. Changes nothing." },
];
// Header and rows share one grid so the columns line up without a table element.
const COLUMNS =
	"grid grid-cols-[minmax(0,2fr)_minmax(0,2fr)_minmax(0,1fr)_2rem] items-center gap-4";

const isAdding = ref(false);

const teamOverview = useTeamOverview();

const team = computed(() => teamOverview.data);

const canManage = computed(() => MANAGING_ROLES.includes(team.value?.my_role ?? ""));

// Members and pending invitations share one list so the table reads as the whole team,
// with the people who have not accepted yet at the bottom.
const rows = computed<Row[]>(() => [
	...(team.value?.members ?? []).map(memberRow),
	...(team.value?.invites ?? []).map(inviteRow),
]);

interface Row {
	key: string;
	name: string;
	email: string;
	role: string;
	image?: string;
	member?: TeamMember;
}

function memberRow(member: TeamMember): Row {
	return {
		key: member.user,
		name: member.full_name ?? member.user,
		email: member.user,
		role: member.team_role,
		image: member.user_image ?? undefined,
		member,
	};
}

// There is no user yet, so no name and no image — the address stands in for both.
function inviteRow(invite: TeamInvite): Row {
	return {
		key: `invite:${invite.email}`,
		name: invite.email,
		email: invite.email,
		role: invite.team_role,
	};
}

// The owner is locked server-side, leaving a team is its own flow rather than a
// self-removal, and an invitation is revoked rather than removed.
function canRemove(row: Row) {
	if (!canManage.value || !row.member) return false;
	return row.member.team_role !== "Owner" && row.member.user !== session.user;
}

function actionsFor(row: Row) {
	return [
		{
			label: "Remove from team",
			icon: "trash-2",
			theme: "red" as const,
			onClick: () => confirmRemove(row),
		},
	];
}

function confirmRemove(row: Row) {
	dialog.confirm({
		title: "Remove member",
		message: `${row.name} will lose access to this team.`,
		theme: "red",
		confirmLabel: "Remove",
		// A rejected promise renders inline in the dialog, so failures need no branch here.
		onConfirm: async () => {
			await removeMember.submit({ team: currentTeam.value?.name, user: row.email });
			await teamOverview.reload();
			toast.success(`${row.name} was removed from the team.`);
		},
	});
}
</script>

<template>
	<TeamPageHeader title="Members" />

	<div class="m-auto max-w-[900px] w-full py-8 px-4 space-y-6">
		<LoadingText v-if="teamOverview.loading" text="Loading members…" />

		<ErrorMessage v-else-if="teamOverviewError" :message="teamOverviewError" />

		<template v-else-if="team">
			<header class="space-y-1">
				<h1 class="font-semibold text-4xl">Team members</h1>
				<p class="text-base text-ink-gray-5">
					Everyone who works on {{ team.team_name }}, and what they are allowed to do.
				</p>
			</header>

			<section class="rounded-xl bg-surface-gray-1 p-4">
				<h2 class="text-sm font-medium text-ink-gray-7">What each role can do</h2>
				<dl class="mt-3 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
					<div v-for="role in ROLES" :key="role.name" class="flex gap-2">
						<dt class="w-20 shrink-0 font-medium text-ink-gray-7">{{ role.name }}</dt>
						<dd class="text-ink-gray-5">{{ role.can }}</dd>
					</div>
				</dl>
			</section>

			<div>
				<div class="flex justify-end pb-3">
					<Button
						v-if="canManage"
						icon-left="plus"
						label="Add member"
						@click="isAdding = true"
					/>
				</div>

				<div :class="COLUMNS" class="pb-2 text-sm text-ink-gray-5">
					<span>Name</span>
					<span>Email</span>
					<span>Role</span>
				</div>

				<!-- Removing a row would otherwise snap the rest of the list upwards. -->
				<TransitionGroup tag="ul" name="member" aria-label="Team members" class="relative">
					<li
						v-for="row in rows"
						:key="row.key"
						:class="COLUMNS"
						class="-mx-2 rounded px-2 py-2 transition-colors duration-150 hover:bg-surface-gray-1"
					>
						<div class="flex min-w-0 items-center gap-3">
							<Avatar :image="row.image" :label="row.name" size="lg" />
							<span class="truncate text-base text-ink-gray-8">{{ row.name }}</span>
						</div>

						<span class="truncate text-base text-ink-gray-6">{{ row.email }}</span>

						<span class="truncate text-base font-medium text-ink-gray-8">
							{{ row.role }}
							<span v-if="!row.member" class="font-normal text-ink-gray-5">
								(Invited)
							</span>
						</span>

						<Dropdown v-if="canRemove(row)" :options="actionsFor(row)" align="end">
							<!-- label is the accessible name here: an icon slot makes it icon-only. -->
							<Button variant="ghost" label="Member actions">
								<template #icon>
									<span class="lucide-ellipsis size-4" />
								</template>
							</Button>
						</Dropdown>
					</li>
				</TransitionGroup>
			</div>

			<AddMembersDialog
				v-model="isAdding"
				:team="currentTeam?.name ?? ''"
				@success="teamOverview.reload()"
			/>
		</template>
	</div>
</template>

<style scoped>
/* The leaving row is taken out of flow so the rows below start closing the gap
   straight away rather than waiting for the fade to finish. */
.member-leave-active {
	position: absolute;
	inset-inline: 0;
	transition: opacity 150ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 150ms cubic-bezier(0.23, 1, 0.32, 1);
}

.member-leave-to {
	opacity: 0;
	transform: translateX(0.5rem);
}

.member-move {
	transition: transform 250ms cubic-bezier(0.23, 1, 0.32, 1);
}

@media (prefers-reduced-motion: reduce) {
	.member-leave-to {
		transform: none;
	}

	.member-move {
		transition: none;
	}
}
</style>
