import type { BuzzPrice } from "../Events/BuzzPrice"
import type { BuzzCouponTicketType } from "./BuzzCouponTicketType"

export interface BuzzCouponCode {
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
	/**	Coupon Type : Select	*/
	coupon_type: "Promo Code" | "Automatic"
	/**	Code : Data	*/
	code?: string
	/**	Enabled : Check	*/
	enabled?: 0 | 1
	/**	Description : Small Text	*/
	description?: string
	/**	Discount Type : Select	*/
	discount_type: "Percentage" | "Flat Amount"
	/**	Discount Percentage : Percent	*/
	discount_percentage?: number
	/**	Discount Amounts : Table - Buzz Price	*/
	discount_amounts?: BuzzPrice[]
	/**	Applies to All Ticket Types : Check	*/
	applies_to_all_ticket_types?: 0 | 1
	/**	Ticket Types : Table MultiSelect - Buzz Coupon Ticket Type	*/
	ticket_types?: BuzzCouponTicketType[]
	/**	Minimum Requirement : Select	*/
	minimum_requirement?: "" | "Minimum Order Amount" | "Minimum Ticket Count"
	/**	Minimum Order Amounts : Table - Buzz Price	*/
	minimum_order_amounts?: BuzzPrice[]
	/**	Minimum Ticket Count : Int	*/
	minimum_ticket_count?: number
	/**	Usage Limit : Int	*/
	usage_limit?: number
	/**	Once per Buyer : Check	*/
	once_per_buyer?: 0 | 1
	/**	Expires On : Date - Usable through the whole day	*/
	expires_on?: string
}
