import { type RouteRecordRaw, createRouter, createWebHistory } from "vue-router"

import { isTeamMember } from "@/data/teams"
import { loadUser } from "@/data/user"

const APP_NAME = "Buzz"

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
				meta: { title: "My Events" },
				component: () => import("@/pages/manage/MyEvents.vue"),
			},
			{
				path: "events/:eventId",
				redirect: (to) => `/manage/events/${to.params.eventId}/details`,
			},
			{
				path: "events/:eventId/details",
				name: "event-details",
				meta: { title: "Details" },
				component: () => import("@/pages/manage/events/EventDetails.vue"),
			},
			{
				path: "events/:eventId/registrations",
				name: "event-registrations",
				meta: { title: "Registration" },
				component: () => import("@/pages/manage/events/EventRegistrations.vue"),
			},
			{
				path: "events/:eventId/guests",
				name: "event-guests",
				meta: { title: "Guests" },
				component: () => import("@/pages/manage/events/EventGuests.vue"),
			},
			{
				path: "events/:eventId/talks",
				name: "event-talks",
				meta: { title: "Talks" },
				component: () => import("@/pages/manage/events/EventTalks.vue"),
			},
			{
				path: "events/:eventId/communications",
				name: "event-communications",
				meta: { title: "Announcements" },
				component: () => import("@/pages/manage/events/EventCommunications.vue"),
			},
			{
				path: "events/:eventId/sponsorships",
				name: "event-sponsorships",
				meta: { title: "Sponsorships" },
				component: () => import("@/pages/manage/events/EventSponsorships.vue"),
			},
			{
				path: "events/:eventId/more",
				name: "event-more",
				meta: { title: "More" },
				component: () => import("@/pages/manage/events/EventMore.vue"),
			},
			{
				path: "events/:eventId/:section",
				component: () => import("@/pages/manage/WorkInProgress.vue"),
			},
			{
				path: "team/events/new",
				name: "create-event",
				meta: { title: "Create New Event" },
				component: () => import("@/pages/manage/events/CreateEvent.vue"),
			},
			{
				path: "communities",
				name: "communities",
				meta: { title: "Communities" },
				component: () => import("@/pages/manage/MyTeams.vue"),
			},
			{
				// Old links from before teams were called communities.
				path: "teams/:rest(.*)*",
				redirect: (to) => to.fullPath.replace("/manage/teams", "/manage/communities"),
			},
			{
				path: "communities/:teamId",
				redirect: (to) => `/manage/communities/${to.params.teamId}/calendar`,
			},
			{
				// Old links from before the page was called Calendar.
				path: "communities/:teamId/events",
				redirect: (to) => `/manage/communities/${to.params.teamId}/calendar`,
			},
			{
				path: "communities/:teamId/calendar",
				name: "team-calendar",
				meta: { title: "Calendar" },
				component: () => import("@/pages/manage/MyEvents.vue"),
			},
			{
				path: "communities/:teamId/members",
				name: "team-members",
				meta: { title: "Members" },
				component: () => import("@/pages/manage/teams/TeamMembers.vue"),
			},
			{
				path: "communities/:teamId/payments",
				name: "team-payments",
				meta: { title: "Payments" },
				component: () => import("@/pages/manage/teams/TeamPayments.vue"),
			},
			{
				// One record with an optional section, so the form survives the list and back.
				path: "communities/:teamId/settings/:section?",
				name: "team-settings",
				meta: { title: "Settings", hideMobileNavWith: "section" },
				component: () => import("@/pages/manage/teams/TeamSettings.vue"),
			},
			{
				path: "proposals",
				name: "proposals",
				meta: { title: "My Proposals" },
				component: () => import("@/pages/manage/MyProposals.vue"),
			},
			// Sidebar destinations that have no page yet. Unnamed on purpose: SidebarItem
			// falls back to matching on path, so each one lights up on its own. Enumerated
			// so a mistyped path reaches the 404 below — keep in step with the sidebar
			// items in ManagerLayout.vue.
			{
				path: ":section(sponsorship|overview|registrations|sponsors|more)",
				component: () => import("@/pages/manage/WorkInProgress.vue"),
			},
			// Claims the rest of /manage before the two-segment custom form route can:
			// /manage/anything otherwise reads as an event route and a form route.
			{
				path: ":pathMatch(.*)*",
				component: () => import("@/pages/NotFound.vue"),
			},
		],
	},
	{
		path: "/check-in/:eventName?",
		name: "check-in",
		props: true,
		meta: { title: "Check In" },
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
		path: "/login",
		name: "login",
		meta: { isPublic: true, title: "Log In" },
		component: () => import("@/pages/LoginPage.vue"),
	},
	{
		path: "/login/embed",
		name: "login-embed",
		meta: { isPublic: true, embedded: true },
		component: () => import("@/pages/LoginEmbed.vue"),
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
		meta: { isPublic: true, title: "Booking Confirmed" },
		component: () => import("@/pages/BookingSuccess.vue"),
	},
	{
		path: "/register-interest/:campaign",
		props: true,
		name: "register-interest",
		meta: { title: "Register Interest" },
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
				meta: { title: "My Bookings" },
				component: () => import("@/pages/BookingsList.vue"),
			},
			{
				path: "bookings/:bookingId",
				props: true,
				name: "booking-details",
				meta: { title: "Booking Details" },
				component: () => import("@/pages/BookingDetails.vue"),
			},
			{
				path: "tickets",
				name: "tickets-list",
				meta: { title: "My Tickets" },
				component: () => import("@/pages/TicketsList.vue"),
			},
			{
				path: "tickets/:ticketId",
				props: true,
				name: "ticket-details",
				meta: { title: "Ticket Details" },
				component: () => import("@/pages/TicketDetails.vue"),
			},
			{
				path: "proposals",
				name: "proposals-list",
				meta: { title: "Talk Proposals" },
				component: () => import("@/pages/ProposalsList.vue"),
			},
			{
				path: "proposals/:proposalId",
				props: true,
				name: "proposal-details",
				meta: { title: "Proposal Details" },
				component: () => import("@/pages/ProposalDetails.vue"),
			},
			{
				path: "sponsorships",
				name: "sponsorships-list",
				meta: { title: "Sponsorships" },
				component: () => import("@/pages/SponsorshipsList.vue"),
			},
			{
				path: "sponsorships/:enquiryId",
				props: true,
				name: "sponsorship-details",
				meta: { title: "Sponsorship Details" },
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
		meta: { isPublic: true, title: "Not Found" },
		component: () => import("@/pages/NotFound.vue"),
	},
]

const router = createRouter({
	history: createWebHistory("/b"),
	routes,
})

router.beforeEach(async (to, from, next) => {
	const userLoaded = loadUser()
	// The manager shell reads user info reactively, so its pages render their skeletons
	// while it loads.
	if (!to.meta.fullBleed) await userLoaded
	next()
})

router.afterEach((to, from) => {
	// Skipped on a same-path navigation: a usePageMeta watcher built only on loaded
	// data won't rerun, so overwriting here would strand the generic title.
	if (to.path === from.path) return
	const title = to.meta.title as string | undefined
	document.title = title ? `${__(title)} | ${APP_NAME}` : APP_NAME
})

export default router
