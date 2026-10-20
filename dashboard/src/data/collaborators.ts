import { call, useCall, useList } from "frappe-ui"

import type { EventCollaborator, InviteOutcome } from "@/types"
import type { SectionLevels } from "@/utils/eventSections"

const API = "/api/v2/method/buzz.api.events.collaborators"

export function useCollaborators(event: string) {
	return useList<EventCollaborator>({
		doctype: "Buzz Event Collaborator",
		filters: { event, status: ["!=", "Revoked"] },
		fields: [
			"name",
			"email",
			"user",
			"status",
			"details_access",
			"guests_access",
			"ticketing_access",
			"talks_access",
			"sponsors_access",
			"communications_access",
		],
		orderBy: "creation asc",
		limit: 200,
	})
}

export function useInviteCollaborators() {
	return useCall<
		InviteOutcome[],
		{ event: string; invites: ({ email: string } & Partial<SectionLevels>)[] }
	>({ url: `${API}.invite_collaborators`, method: "POST", immediate: false })
}

export function useUpdateCollaboratorAccess() {
	return useCall<null, { event: string; email: string; sections: SectionLevels }>({
		url: `${API}.update_collaborator_access`,
		method: "POST",
		immediate: false,
	})
}

export function useRevokeCollaborators() {
	return useCall<null, { event: string; emails: string[] }>({
		url: `${API}.revoke_collaborators`,
		method: "POST",
		immediate: false,
	})
}

export function useAcceptCollaboratorInvite() {
	return useCall<{ redirect_to: string }, { key: string }>({
		url: `${API}.accept_collaborator_invite`,
		method: "POST",
		immediate: false,
	})
}

let collaborating: Promise<boolean> | null = null

/** Whether the session user collaborates on any event. Asked once; the answer is per session. */
export function hasCollaborations(): Promise<boolean> {
	// A failed answer is not kept, so the next navigation asks again.
	collaborating ??= call<boolean>("buzz.api.events.collaborators.has_collaborations").catch(() => {
		collaborating = null
		return false
	})
	return collaborating
}
