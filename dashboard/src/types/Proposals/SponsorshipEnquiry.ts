export interface SponsorshipEnquiry {
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
	/**	Event : Link - Buzz Event	*/
	event: string
	/**	Company Name : Data	*/
	company_name: string
	/**	Company Logo : Attach Image	*/
	company_logo: string
	/**	Website : Data	*/
	website?: string
	/**	Status : Select	*/
	status?: "Approval Pending" | "Payment Pending" | "Paid" | "Cancelled" | "Withdrawn"
	/**	Tier : Link - Sponsorship Tier	*/
	tier?: string
	/**	Country : Link - Country	*/
	country?: string
	/**	Phone : Phone	*/
	phone?: string
}
