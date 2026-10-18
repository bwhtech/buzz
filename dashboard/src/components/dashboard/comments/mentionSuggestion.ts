import { SuggestionExtension } from "frappe-ui/editor"
import { type MaybeRefOrGetter, toValue } from "vue"

import type { TeamMember } from "@/types"

import MentionList, { type MentionItem } from "./MentionList.vue"

const toItem = (member: TeamMember): MentionItem => ({
	id: member.user,
	label: member.full_name || member.user,
	image: member.user_image,
	role: member.team_role,
})

/**
 * "@" opens team members with their avatars. CommentKit's own list shows names only, so
 * it is left unconfigured and this inserts the same `mention` node, which Frappe's
 * extract_mentions reads by its `data-id`.
 */
export function mentionSuggestion(members: MaybeRefOrGetter<TeamMember[]>) {
	return SuggestionExtension.configure<MentionItem>({
		name: "teamMention",
		trigger: "@",
		allowSpaces: true,
		listComponent: MentionList,
		floatingOptions: { placement: "top-start", offset: 6 },
		items: (query) =>
			toValue(members)
				.map(toItem)
				.filter((item) => item.label.toLowerCase().includes(query.toLowerCase()))
				.slice(0, 8),
		command: ({ editor, item, range }) =>
			editor
				.chain()
				.focus()
				.insertContentAt(range, [
					{ type: "mention", attrs: { id: item.id, label: item.label } },
					{ type: "text", text: " " },
				])
				.run(),
	})
}
