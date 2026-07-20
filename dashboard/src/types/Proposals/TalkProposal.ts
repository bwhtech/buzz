import type { ProposalSpeaker } from "./ProposalSpeaker"

export interface TalkProposal {
	name: string
	creation: string
	modified: string
	owner: string
	modified_by: string
	docstatus: 0 | 1 | 2
	parent?: string
	parentfield?: string
	parenttype?: string
	idx?: number
	/**	Title : Data	*/
	title: string
	/**	Submitted By : Link - User	*/
	submitted_by?: string
	/**	Status : Link - Talk Proposal Status	*/
	status?: string
	/**	Event : Link - Buzz Event	*/
	event: string
	/**	Description : Text Editor	*/
	description?: string
	/**	Speakers : Table - Proposal Speaker	*/
	speakers?: ProposalSpeaker[]
	/**	Phone : Phone	*/
	phone?: string
}
