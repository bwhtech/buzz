import { userResource } from "@/data/user"
import { type RouteRecordRaw, createRouter, createWebHistory } from "vue-router"

const routes: RouteRecordRaw[] = [
	{
		path: "/",
		name: "dashboard",
		redirect: { name: "bookings-tab" },
	},
	{
		path: "/check-in/:eventName?",
		name: "check-in",
		props: true,
		component: () => import("@/pages/CheckInScanner.vue"),
	},
	{
		path: "/register/:eventRoute",
		props: true,
		name: "event-booking",
		meta: { isPublic: true },
		component: () => import("@/pages/BookTickets.vue"),
	},
	{
		path: "/event-proposal",
		name: "event-proposal",
		meta: { isPublic: true },
		component: () => import("@/pages/EventProposalForm.vue"),
	},
	{
		path: "/booking-success/:bookingId",
		name: "booking-success",
		props: true,
		meta: { isPublic: true },
		component: () => import("@/pages/BookingSuccess.vue"),
	},
	{
		path: "/register-interest/:campaign",
		props: true,
		name: "register-interest",
		component: () => import("@/pages/RegisterInterest.vue"),
	},
	// Back-compat: old in-app paths redirect to the shortened scheme.
	{
		path: "/book-tickets/:eventRoute",
		redirect: (to) => ({ name: "event-booking", params: to.params }),
	},
	{
		path: "/events/:eventRoute/forms/:formRoute",
		redirect: (to) => ({ name: "custom-form", params: to.params }),
	},
	{
		path: "/bookings",
		name: "bookings-tab",
		redirect: "/account/bookings",
	},
	{
		path: "/bookings/:bookingId",
		redirect: (to) => ({
			name: "booking-details",
			params: { bookingId: to.params.bookingId },
		}),
	},
	{
		path: "/tickets",
		redirect: "/account/tickets",
	},
	{
		path: "/tickets/:ticketId",
		redirect: (to) => ({
			name: "ticket-details",
			params: { ticketId: to.params.ticketId },
		}),
	},
	{
		path: "/account",
		component: () => import("@/pages/Account.vue"),
		redirect: { name: "bookings-list" },
		children: [
			{
				path: "bookings",
				name: "bookings-list",
				component: () => import("@/pages/BookingsList.vue"),
			},
			{
				path: "bookings/:bookingId",
				props: true,
				name: "booking-details",
				component: () => import("@/pages/BookingDetails.vue"),
			},
			{
				path: "tickets",
				name: "tickets-list",
				component: () => import("@/pages/TicketsList.vue"),
			},
			{
				path: "tickets/:ticketId",
				props: true,
				name: "ticket-details",
				component: () => import("@/pages/TicketDetails.vue"),
			},
			{
				path: "proposals",
				name: "proposals-list",
				component: () => import("@/pages/ProposalsList.vue"),
			},
			{
				path: "proposals/:proposalId",
				props: true,
				name: "proposal-details",
				component: () => import("@/pages/ProposalDetails.vue"),
			},
			{
				path: "sponsorships",
				name: "sponsorships-list",
				component: () => import("@/pages/SponsorshipsList.vue"),
			},
			{
				path: "sponsorships/:enquiryId",
				props: true,
				name: "sponsorship-details",
				component: () => import("@/pages/SponsorshipDetails.vue"),
			},
		],
	},
	// Event custom form: /b/<event>/<form>. Declared last — two dynamic segments,
	// so it only matches after every static route above has been ruled out.
	{
		path: "/:eventRoute/:formRoute",
		props: true,
		name: "custom-form",
		meta: { isPublic: true },
		component: () => import("@/pages/CustomFormPage.vue"),
	},
]

const router = createRouter({
	history: createWebHistory("/b"),
	routes,
})

router.beforeEach(async (to, from, next) => {
	try {
		await userResource.fetch()
	} catch {
		// user is not logged in — Layout will show LoginRequired for protected routes
	}
	next()
})

export default router
