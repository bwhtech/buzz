import { computed, ref } from "vue"

import { emailKey as key, INVITE_LIMIT, type Invitee, newInvitee } from "./invites"

type Removed = { invitee: Invitee; index: number }
type Change = { added: Invitee[]; typed: boolean } | { removed: Removed[] }

/** The people picked for one invite batch, capped at the limit, with an undo history. */
export function useInviteSelection(defaultTier: () => string) {
	const selected = ref<Invitee[]>([])
	const history = ref<Change[]>([])

	const remaining = computed(() => INVITE_LIMIT - selected.value.length)
	const isSelected = (email: string) => selected.value.some((row) => key(row.email) === key(email))

	/** Adds whoever is new, up to the limit; returns how many did not fit. */
	function add(people: Partial<Invitee>[], typed = false): number {
		const fresh = people.filter(
			(person, index) =>
				person.email &&
				!isSelected(person.email) &&
				people.findIndex((other) => key(other.email ?? "") === key(person.email ?? "")) === index,
		)
		const added = fresh
			.slice(0, Math.max(remaining.value, 0))
			.map((person) => newInvitee({ ticket_type: defaultTier(), ...person }))
		if (added.length) {
			selected.value.push(...added)
			history.value.push({ added, typed })
		}
		return fresh.length - added.length
	}

	function remove(people: Invitee[]) {
		const removed = people
			.map((invitee) => ({ invitee, index: selected.value.indexOf(invitee) }))
			.filter((entry) => entry.index >= 0)
		if (!removed.length) return
		selected.value = selected.value.filter((row) => !people.includes(row))
		history.value.push({ removed })
	}

	const removeEmail = (email: string) =>
		remove(selected.value.filter((row) => key(row.email) === key(email)))

	/** Reverts the last change and returns it, so typed addresses can go back to the box. */
	function undo(): Change | undefined {
		const change = history.value.pop()
		if (!change) return undefined
		if ("added" in change)
			selected.value = selected.value.filter((row) => !change.added.includes(row))
		else
			for (const { invitee, index } of change.removed.toSorted((a, b) => a.index - b.index))
				selected.value.splice(index, 0, invitee)
		return change
	}

	function reset() {
		selected.value = []
		history.value = []
	}

	return { selected, remaining, isSelected, add, remove, removeEmail, undo, reset }
}

export type InviteSelection = ReturnType<typeof useInviteSelection>
