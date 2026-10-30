export interface BuzzCouponTicketType {
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
	/**	Ticket Type : Link - Event Ticket Type	*/
	ticket_type: string
}
