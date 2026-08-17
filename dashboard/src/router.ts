import { isTeamMember } from "@/data/teams"
import { userResource } from "@/data/user"
import { type RouteRecordRaw, createRouter, createWebHistory } from "vue-router"

const routes: RouteRecordRaw[] = [
	{
		path: "/",
		name: "dashboard",
		// Never rendered — the guard always redirects — but a record needs a component.
		component: { render: () => null },
		beforeEnter: async () => ({
			name: (await isTeamMember()) ? "manage" : "bookings-tab",
		}),
	},
	{
		path: "/manage",
		meta: { fullBleed: true },
		component: () => import("@/layouts/ManagerLayout.vue"),
		children: [
			{
				path: "",
				name: "manage",
				redirect: { name: "events" },
			},
			{
				path: "events",
				name: "events",
				component: () => import("@/pages/manage/MyEvents.vue"),
			},
			// Sidebar destinations that have no page yet. Unnamed on purpose: SidebarItem
			// falls back to matching on path, so each one lights up on its own. Enumerated
			// so a mistyped path falls through to the 404 instead — keep in step with the
			// sidebar items in ManagerLayout.vue.
			{
				path: ":section(tickets|proposals|sponsorship|overview|registrations|sponsors|more)",
				component: () => import("@/pages/manage/WorkInProgress.vue"),
			},
		],
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
	// Last: everything above must be ruled out before a path counts as unknown.
	{
		path: "/:pathMatch(.*)*",
		name: "not-found",
		meta: { isPublic: true },
		component: () => import("@/pages/NotFound.vue"),
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

const defaultTitle = document.title

router.afterEach((to, from) => {
	// Pages set their own title via usePageMeta, which never restores it on
	// unmount. Reset here so a page without one doesn't keep showing the
	// previous page's title. Same-path navigation keeps the title: usePageMeta's
	// watcher won't refire when its data is unchanged, so resetting would stick.
	if (to.path !== from.path) document.title = defaultTitle
})

export default router
