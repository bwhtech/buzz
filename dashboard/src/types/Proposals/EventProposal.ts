export interface EventProposal {
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
	/**	Event Category : Link - Event Category	*/
	category: string
	/**	Free Event? : Check	*/
	free_event?: 0 | 1
	/**	Medium : Select	*/
	medium: "Online" | "In Person"
	/**	Status : Select	*/
	status?: "Received" | "In Review" | "Approved" | "Event Created" | "Rejected"
	/**	Naming Series : Select	*/
	naming_series?: "EPR-.###"
	/**	Start Date : Date	*/
	start_date: string
	/**	Start Time : Time	*/
	start_time?: string
	/**	End Date : Date	*/
	end_date?: string
	/**	End Time : Time	*/
	end_time?: string
	/**	Short Description : Small Text	*/
	short_description?: string
	/**	About the event : Text Editor	*/
	about: string
	/**	Host : Link - Event Host - Required for creating an event	*/
	host?: string
	/**	Host Company : Data	*/
	host_company?: string
	/**	Additional Notes : Small Text	*/
	additional_notes?: string
	/**	Host Company Logo : Attach Image	*/
	host_company_logo?: string
	/**	Amended From : Link - Event Proposal	*/
	amended_from?: string
}
