<template>
	<ProfileView />

	<!-- Mobile: Select dropdown for navigation -->
	<div class="sm:hidden">
		<FormControl
			type="select"
			:modelValue="currentTabRoute"
			:options="selectOptions"
			@update:modelValue="onSelectChange"
		/>
	</div>

	<!-- Desktop: Tabs for navigation. Unbound in route mode, so selection follows
	     the URL; the key re-mounts the list when the async Sponsorships tab lands. -->
	<div class="hidden sm:block">
		<Tabs as="div" :key="tabs.length" :tabs="tabs">
			<template #tab-panel>
				<div></div>
			</template>
		</Tabs>
	</div>

	<div class="py-5">
		<router-view></router-view>
	</div>
</template>

<script setup lang="ts">
import { Tabs, createResource } from "frappe-ui"
import { computed, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import LucideCalendarDays from "~icons/lucide/calendar-days"
import LucideCircleDollarSign from "~icons/lucide/circle-dollar-sign"
import LucideMegaphone from "~icons/lucide/megaphone"
import LucideTicket from "~icons/lucide/ticket"

import ProfileView from "@/components/ProfileView.vue"

const route = useRoute()
const router = useRouter()

const sponsorships = createResource({
	url: "buzz.api.sponsorships.get_user_sponsorship_inquiries",
	auto: true,
	cacheKey: "account-sponsorships-check",
	onError: console.error,
})

const tabs = computed(() => {
	const accountTabs = [
		{
			value: "/account/bookings",
			label: __("My Bookings"),
			route: "/account/bookings",
			iconLeft: LucideCalendarDays,
		},
		{
			value: "/account/tickets",
			label: __("My Tickets"),
			route: "/account/tickets",
			iconLeft: LucideTicket,
		},
		{
			value: "/account/proposals",
			label: __("Talk Proposals"),
			route: "/account/proposals",
			iconLeft: LucideMegaphone,
		},
	]

	if (sponsorships.data?.length) {
		accountTabs.push({
			value: "/account/sponsorships",
			label: __("Sponsorships"),
			route: "/account/sponsorships",
			iconLeft: LucideCircleDollarSign,
		})
	}

	return accountTabs
})

const selectOptions = computed(() =>
	tabs.value.map((tab) => ({
		label: tab.label,
		value: tab.route,
	})),
)

const currentTabRoute = computed(() => {
	const tab = tabs.value.find((candidate) => route.path.startsWith(candidate.route))
	return tab ? tab.route : tabs.value[0].route
})

function onSelectChange(value: string) {
	router.push(value)
}

// An unknown /account/* path matches no tab, so send it to the first one — but
// only once the async Sponsorships tab has settled, or /account/sponsorships
// would bounce away before its tab exists.
watch(
	[() => route.path, () => tabs.value.length, () => sponsorships.loading],
	() => {
		const onKnownTab = tabs.value.some((tab) => route.path.startsWith(tab.route))
		if (!onKnownTab && !sponsorships.loading && route.path.startsWith("/account/")) {
			router.replace(tabs.value[0].route)
		}
	},
	{ immediate: true },
)
</script>
