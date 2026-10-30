import type { AdditionalField } from "./AdditionalField"
import type { TicketAddOnValue } from "./TicketAddOnValue"

export interface EventTicket {
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
	/**	First Name : Data	*/
	first_name: string
	/**	Last Name : Data	*/
	last_name?: string
	/**	Attendee Name : Data	*/
	attendee_name: string
	/**	Event : Link - Buzz Event	*/
	event?: string
	/**	Booking : Link - Event Booking	*/
	booking?: string
	/**	Attendee Email : Data	*/
	attendee_email: string
	/**	Ticket Type : Link - Event Ticket Type	*/
	ticket_type: string
	/**	QR Code : Attach Image	*/
	qr_code?: string
	/**	Additional Fields : Table - Additional Field	*/
	additional_fields?: AdditionalField[]
	/**	Add Ons : Table - Ticket Add-on Value	*/
	add_ons?: TicketAddOnValue[]
	/**	Amended From : Link - Event Ticket	*/
	amended_from?: string
}
