<script setup lang="ts">
import { MobileNav, MobileNavItem, MobileShell } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import MobileMoreSheet from "@/components/dashboard/MobileMoreSheet.vue"
import WorkspaceOpening from "@/components/dashboard/WorkspaceOpening.vue"
import UserMenu from "@/components/UserMenu.vue"
import { discoverEvents, openDiscoverEvents, type ManagerNavItem } from "@/utils/managerNavigation"

const props = defineProps<{ items: ManagerNavItem[]; showDiscover?: boolean }>()

// A phone fits five tabs; past that, the fifth opens a sheet holding the rest.
const MAX_TABS = 5
const tabs = computed(() =>
	props.items.length > MAX_TABS ? props.items.slice(0, MAX_TABS - 1) : props.items,
)
const overflow = computed(() => props.items.slice(tabs.value.length))

const moreOpen = ref(false)
const accountOpen = ref(false)

// `active` is a Boolean prop, so leaving it unset casts to false and skips route matching.
const route = useRoute()

// A route can drop the nav while one of its params is set, as a full-screen sub-page.
const showNav = computed(() => {
	const param = route.meta.hideMobileNavWith as string | undefined
	return !(param && route.params[param])
})
</script>

<template>
	<MobileShell>
		<div class="relative min-h-full bg-surface-elevation-1">
			<router-view :key="$route.params.eventId as string" />
			<WorkspaceOpening />
		</div>

		<template #nav>
			<Transition name="mobile-nav">
				<MobileNav v-if="items.length && showNav">
					<MobileNavItem
						v-for="item in tabs"
						:key="item.label"
						:label="item.shortLabel ?? item.label"
						:icon="item.icon"
						:route="item.to"
						:active="route.path === item.to"
					/>
					<MobileNavItem
						v-if="showDiscover"
						:label="discoverEvents.shortLabel"
						:icon="discoverEvents.icon"
						@click="openDiscoverEvents"
					/>
					<MobileNavItem
						v-if="overflow.length"
						:label="__('More')"
						icon="lucide-ellipsis"
						:active="moreOpen || overflow.some((item) => item.to === route.path)"
						@click="moreOpen = true"
					/>
				</MobileNav>
			</Transition>

			<template v-if="overflow.length">
				<MobileMoreSheet v-model:open="moreOpen" :items="overflow" @account="accountOpen = true" />
				<UserMenu v-model:sheet-open="accountOpen" variant="sheet" hide-trigger />
			</template>
		</template>
	</MobileShell>
</template>

<style scoped>
.mobile-nav-enter-active {
	transition: transform 220ms cubic-bezier(0.32, 0.72, 0, 1);
}

.mobile-nav-leave-active {
	transition: transform 160ms cubic-bezier(0.32, 0.72, 0, 1);
}

.mobile-nav-enter-from,
.mobile-nav-leave-to {
	transform: translateY(100%);
}

@media (prefers-reduced-motion: reduce) {
	.mobile-nav-enter-active,
	.mobile-nav-leave-active {
		transition: none;
	}
}
</style>
