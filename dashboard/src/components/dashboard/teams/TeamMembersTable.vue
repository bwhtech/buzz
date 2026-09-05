<script setup lang="ts">
import { Avatar, Button, Dropdown, dialog, toast } from "frappe-ui"
import { computed } from "vue"

import { session } from "@/data/session"
import { removeMember } from "@/data/teams"
import type { TeamInvite, TeamMember, TeamOverview } from "@/types"

const props = defineProps<{ team: TeamOverview }>()
const emit = defineEmits<{ removed: [] }>()

const MANAGING_ROLES = ["Owner", "Admin"]
// Header and rows share one grid so the columns line up without a table element.
const COLUMNS = "grid grid-cols-[minmax(0,2fr)_minmax(0,2fr)_minmax(0,1fr)_2rem] items-center gap-4"

interface Row {
	key: string
	name: string
	email: string
	role: string
	image?: string
	member?: TeamMember
}

const canManage = computed(() => MANAGING_ROLES.includes(props.team.my_role))

// Members and pending invitations share one list so the table reads as the whole team,
// with the people who have not accepted yet at the bottom.
const rows = computed<Row[]>(() => [
	...props.team.members.map(memberRow),
	...props.team.invites.map(inviteRow),
])

function memberRow(member: TeamMember): Row {
	return {
		key: member.user,
		name: member.full_name ?? member.user,
		email: member.user,
		role: member.team_role,
		image: member.user_image ?? undefined,
		member,
	}
}

// There is no user yet, so no name and no image — the address stands in for both.
function inviteRow(invite: TeamInvite): Row {
	return {
		key: `invite:${invite.email}`,
		name: invite.email,
		email: invite.email,
		role: invite.team_role,
	}
}

// The owner is locked server-side, leaving a team is its own flow rather than a
// self-removal, and an invitation is revoked rather than removed.
function canRemove(row: Row) {
	if (!canManage.value || !row.member) return false
	return row.member.team_role !== "Owner" && row.member.user !== session.user
}

function actionsFor(row: Row) {
	return [
		{
			label: __("Remove from team"),
			icon: "lucide-trash-2",
			theme: "red" as const,
			onClick: () => confirmRemove(row),
		},
	]
}

function confirmRemove(row: Row) {
	dialog.confirm({
		title: __("Remove member"),
		message: __("{0} will lose access to this team.", [row.name]),
		theme: "red",
		confirmLabel: __("Remove"),
		// A rejected promise renders inline in the dialog, so failures need no branch here.
		onConfirm: async () => {
			await removeMember.submit({ team: props.team.name, user: row.email })
			emit("removed")
			toast.success(__("{0} was removed from the team.", [row.name]))
		},
	})
}
</script>

<template>
	<div>
		<div :class="COLUMNS" class="pb-2 text-sm text-ink-gray-5">
			<span />
			<span />
			<span>{{ __("Role") }}</span>
		</div>

		<!-- Removing a row would otherwise snap the rest of the list upwards. -->
		<TransitionGroup tag="ul" name="member" :aria-label="__('Team members')" class="relative">
			<li
				v-for="row in rows"
				:key="row.key"
				:class="COLUMNS"
				class="-mx-2 rounded-4 px-2 py-2 transition-colors duration-150 hover:bg-surface-gray-1"
			>
				<div class="flex min-w-0 items-center gap-3">
					<Avatar :image="row.image" :label="row.name" size="lg" />
					<span class="truncate text-base text-ink-gray-8">{{ row.name }}</span>
				</div>

				<!-- An invite has only an address, already shown as its name. -->
				<span class="truncate text-base text-ink-gray-6">{{ row.member ? row.email : "" }}</span>

				<span class="truncate text-base font-medium text-ink-gray-8">
					{{ row.role }}
					<span v-if="!row.member" class="font-normal text-ink-gray-5">({{ __("Invited") }})</span>
				</span>

				<Dropdown v-if="canRemove(row)" :options="actionsFor(row)" align="end">
					<!-- label is the accessible name here: an icon slot makes it icon-only. -->
					<Button variant="ghost" :label="__('Member actions')">
						<template #icon>
							<span class="lucide-ellipsis size-4" />
						</template>
					</Button>
				</Dropdown>
			</li>
		</TransitionGroup>
	</div>
</template>

<style scoped>
/* The leaving row is taken out of flow so the rows below start closing the gap
   straight away rather than waiting for the fade to finish. */
.member-leave-active {
	position: absolute;
	inset-inline: 0;
	transition:
		opacity 150ms cubic-bezier(0.23, 1, 0.32, 1),
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
