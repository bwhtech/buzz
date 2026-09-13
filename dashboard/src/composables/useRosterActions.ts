import { dialog, toast } from "frappe-ui"

import { useRemoveMembers, useResendInvite, useRetractInvite } from "@/data/teams"
import type { TeamMember } from "@/types"
import type { RosterRow } from "@/utils/teamRoster"

/**
 * What the roster does to a member or an invitation, with the confirmation each one needs.
 * `onDone` reloads the roster behind them.
 */
export function useRosterActions(team: () => string, onDone: () => void) {
	const removeMembers = useRemoveMembers()
	const resendInvite = useResendInvite()
	const retractInvite = useRetractInvite()

	// Nothing the roster shows changes, so it is not reloaded.
	async function resend(row: RosterRow) {
		await resendInvite.submit({ team: team(), email: row.email })
		if (resendInvite.error) return toast.error(resendInvite.error.message)
		toast.success(__("Invitation resent to {0}.", [row.email]))
	}

	// A single row's action is a selection of one, so both paths land here.
	function confirmRemove(members: TeamMember[]) {
		const only = members.length === 1 ? members[0] : null
		const name = only?.full_name || only?.user || ""

		dialog.confirm({
			title: only ? __("Remove member") : __("Remove members"),
			message: only
				? __("{0} will lose access to this team.", [name])
				: __("{0} people will lose access to this team.", [members.length]),
			theme: "red",
			confirmLabel: __("Remove"),
			onConfirm: async () => {
				const users = members.map((member) => member.user)
				await removeMembers.submit({ team: team(), users })
				// useCall settles either way, so the failure has to be rethrown to reach the dialog.
				if (removeMembers.error) throw removeMembers.error

				done(
					only
						? __("{0} was removed from the team.", [name])
						: __("{0} people were removed from the team.", [users.length]),
				)
			},
		})
	}

	function confirmRetract(row: RosterRow) {
		dialog.confirm({
			title: __("Retract invitation"),
			message: __(
				"{0} will be told the invitation was withdrawn, and the link will stop working.",
				[row.email],
			),
			theme: "red",
			confirmLabel: __("Retract"),
			onConfirm: async () => {
				await retractInvite.submit({ team: team(), email: row.email })
				if (retractInvite.error) throw retractInvite.error
				done(__("The invitation to {0} was retracted.", [row.email]))
			},
		})
	}

	function done(message: string) {
		onDone()
		toast.success(message)
	}

	return { resend, confirmRemove, confirmRetract }
}
