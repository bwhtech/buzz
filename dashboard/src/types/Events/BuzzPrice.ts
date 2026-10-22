export interface BuzzPrice {
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
	/**	Currency : Link - Currency	*/
	currency: string
	/**	Price : Currency	*/
	price: number
}
