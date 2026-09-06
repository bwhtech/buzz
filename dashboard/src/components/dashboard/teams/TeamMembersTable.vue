<script setup lang="ts">
import { Avatar, Button, Dropdown, dialog, toast } from "frappe-ui"
import { computed } from "vue"

import { session } from "@/data/session"
import { removeMember, useResendInvite, useRetractInvite } from "@/data/teams"
import type { TeamInvite, TeamMember, TeamOverview } from "@/types"
import { canManageMembers } from "@/utils/teamRoles"

const props = defineProps<{ team: TeamOverview }>()
const emit = defineEmits<{ removed: [] }>()

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

const canManage = computed(() => canManageMembers(props.team.my_role))

const resendInvite = useResendInvite()
const retractInvite = useRetractInvite()

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

// The owner is locked server-side, and leaving a team is its own flow rather than a
// self-removal.
function canRemove(row: Row) {
	if (!canManage.value || !row.member) return false
	return row.member.team_role !== "Owner" && row.member.user !== session.user
}

// An invitation is resent or retracted; only a member is removed.
function actionsFor(row: Row) {
	if (!row.member) return canManage.value ? inviteActions(row) : []
	if (!canRemove(row)) return []
	return [
		{
			label: __("Remove from team"),
			icon: "lucide-trash-2",
			theme: "red" as const,
			onClick: () => confirmRemove(row),
		},
	]
}

function inviteActions(row: Row) {
	return [
		{
			label: __("Resend invitation"),
			icon: "lucide-arrow-up-from-line",
			onClick: () => resend(row),
		},
		{
			label: __("Retract invitation"),
			icon: "lucide-shredder",
			theme: "red" as const,
			onClick: () => confirmRetract(row),
		},
	]
}

// Nothing the table shows changes, so the overview is left alone.
async function resend(row: Row) {
	await resendInvite.submit({ team: props.team.name, email: row.email })
	if (resendInvite.error) return toast.error(resendInvite.error.message)
	toast.success(__("Invitation resent to {0}.", [row.email]))
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

function confirmRetract(row: Row) {
	dialog.confirm({
		title: __("Retract invitation"),
		message: __("{0} will be told the invitation was withdrawn, and the link will stop working.", [
			row.email,
		]),
		theme: "red",
		confirmLabel: __("Retract"),
		onConfirm: async () => {
			await retractInvite.submit({ team: props.team.name, email: row.email })
			// useCall settles either way, so the failure has to be rethrown to reach the dialog.
			if (retractInvite.error) throw retractInvite.error
			emit("removed")
			toast.success(__("The invitation to {0} was retracted.", [row.email]))
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

				<Dropdown v-if="actionsFor(row).length" :options="actionsFor(row)" align="end">
					<!-- label is the accessible name here: an icon slot makes it icon-only. -->
					<Button
						variant="ghost"
						:label="row.member ? __('Member actions') : __('Invitation actions')"
					>
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
