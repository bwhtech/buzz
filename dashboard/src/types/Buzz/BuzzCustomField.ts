export interface BuzzCustomField {
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
	/**	Enabled? : Check	*/
	enabled?: 0 | 1
	/**	Event : Link - Buzz Event	*/
	event: string
	/**	Label : Data	*/
	label: string
	/**	Name : Data	*/
	fieldname?: string
	/**	Mandatory? : Check	*/
	mandatory?: 0 | 1
	/**	Placeholder : Data	*/
	placeholder?: string
	/**	Default Value : Data	*/
	default_value?: string
	/**	Applied To : Select	*/
	applied_to?: "Booking" | "Ticket" | "Feedback"
	/**	Type : Select	*/
	fieldtype: "Data" | "Phone" | "Email" | "Select" | "Date" | "Number" | "Multi Select" | "Text"
	/**	Options : Small Text	*/
	options?: string
	/**	Order : Int	*/
	order?: number
}
