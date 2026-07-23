import type { SponsorshipDeckItem } from "../Proposals/SponsorshipDeckItem"
import type { EventFeaturedSpeaker } from "./EventFeaturedSpeaker"
import type { EventPaymentGateway } from "./EventPaymentGateway"
import type { ScheduleItem } from "./ScheduleItem"

export interface BuzzEvent {
	name: number
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
	/**	Category : Link - Event Category	*/
	category: string
	/**	Free Webinar? : Check	*/
	free_webinar?: 0 | 1
	/**	Medium : Select	*/
	medium?: "In Person" | "Online"
	/**	Banner Image : Attach Image	*/
	banner_image?: string
	/**	Host : Link - Event Host	*/
	host: string
	/**	Venue : Link - Event Venue	*/
	venue?: string
	/**	Start Date : Date	*/
	start_date: string
	/**	Start Time : Time	*/
	start_time?: string
	/**	Time Zone : Autocomplete	*/
	time_zone?: any
	/**	Time Zone Label : Data	*/
	time_zone_label?: string
	/**	End Date : Date	*/
	end_date?: string
	/**	End Time : Time	*/
	end_time?: string
	/**	Short Description : Small Text	*/
	short_description?: string
	/**	About : Text Editor - Description of the event	*/
	about?: string
	/**	Schedule : Table - Schedule Item	*/
	schedule?: ScheduleItem[]
	/**	Is Published? : Check	*/
	is_published?: 0 | 1
	/**	Route : Data - Used by Frappe Builder	*/
	route?: string
	/**	Default Ticket Type : Link - Event Ticket Type - Will be selected by default in the booking form	*/
	default_ticket_type?: string
	/**	External Registration Page? : Check	*/
	external_registration_page?: 0 | 1
	/**	Registration URL : Data	*/
	registration_url?: string
	/**	Meta Image : Attach Image	*/
	meta_image?: string
	/**	Card Image : Attach Image	*/
	card_image?: string
	/**	Featured Speakers : Table - Event Featured Speaker	*/
	featured_speakers?: EventFeaturedSpeaker[]
	/**	Payment Gateways : Table - Event Payment Gateway	*/
	payment_gateways?: EventPaymentGateway[]
	/**	Apply Tax on Bookings? : Check	*/
	apply_tax?: 0 | 1
	/**	Tax Label : Data - Label displayed to customers (e.g., GST, VAT, Sales Tax)	*/
	tax_label?: string
	/**	Tax Percentage : Percent - Tax rate to apply on bookings	*/
	tax_percentage?: number
	/**	Auto Send Pitch Deck? : Check	*/
	auto_send_pitch_deck?: 0 | 1
	/**	Email Template : Link - Email Template - Default template will be used if not set	*/
	sponsor_deck_email_template?: string
	/**	Reply To : Data	*/
	sponsor_deck_reply_to?: string
	/**	CC : Small Text	*/
	sponsor_deck_cc?: string
	/**	Attachments : Table - Sponsorship Deck Item	*/
	sponsor_deck_attachments?: SponsorshipDeckItem[]
	/**	Ticket Email Template : Link - Email Template	*/
	ticket_email_template?: string
	/**	Feedback Email Template : Link - Email Template - Template uses: <code>{{ feedback_link }}</code>, <code>{{ attendee_name }}</code>, and <code>{{ event_title }}</code>.	*/
	feedback_email_template?: string
	/**	Ticket Print Format : Link - Print Format	*/
	ticket_print_format?: string
	/**	Allow Editing Talks After Acceptance : Check - When enabled, speakers can edit their talk title and description after acceptance	*/
	allow_editing_talks_after_acceptance?: 0 | 1
	/**	Proposal : Link - Event Proposal	*/
	proposal?: string
}
