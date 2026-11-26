import type { CouponTicketType } from "@/types"

import type { CouponValues } from "./couponForm"

type CouponType = CouponValues["coupon_type"]
type DiscountType = CouponValues["discount_type"]

const COUPON_TYPES: CouponType[] = ["Promo Code", "Automatic", "Access Code"]

/** Which coupons an event's ticket types allow: discounts need a price, access codes a hidden ticket. */
export class CouponAvailability {
	constructor(private readonly ticketTypes: CouponTicketType[]) {}

	get hasPaid() {
		return this.ticketTypes.some((row) => row.prices.some((price) => price.price > 0))
	}

	get hasHidden() {
		return this.ticketTypes.some((row) => row.is_hidden)
	}

	allowsType(type: CouponType) {
		return type === "Access Code" ? this.hasHidden : this.hasPaid
	}

	allowsDiscount(type: DiscountType) {
		return type === "None" || this.hasPaid
	}

	get firstAllowedType(): CouponType | null {
		return COUPON_TYPES.find((type) => this.allowsType(type)) ?? null
	}

	/** Why discounts are off on this event, or null when a ticket type has a price. */
	get freeEventMessage() {
		if (this.hasPaid) return null
		return this.hasHidden
			? "Your tickets are free, so promo codes and automatic discounts have nothing to take off. Access codes still work for hidden tickets."
			: "Your tickets are free, so there is nothing to discount yet. Add a paid ticket type, or hide one to give out access codes."
	}
}
