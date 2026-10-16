export interface AdditionalEventPage {
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
	/**	Route : Data	*/
	route?: string
	/**	Event : Link - Buzz Event	*/
	event: string
	/**	Is Published? : Check	*/
	is_published?: 0 | 1
	/**	Display Order : Int	*/
	display_order?: number
	/**	Content : Text Editor	*/
	content: string
}
