<script setup lang="ts">
import { MobileNav, MobileNavItem, MobileShell } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import { discoverEvents, openDiscoverEvents, type ManagerNavItem } from "@/utils/managerNavigation"

defineProps<{ items: ManagerNavItem[]; showDiscover?: boolean }>()

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
		<div class="min-h-full bg-surface-elevation-1">
			<router-view />
		</div>

		<template #nav>
			<Transition name="mobile-nav">
				<MobileNav v-if="items.length && showNav">
					<MobileNavItem
						v-for="item in items"
						:key="item.label"
						:label="item.shortLabel ?? item.label"
						:icon="item.icon"
						:to="item.to"
						:active="route.path === item.to"
					/>
					<MobileNavItem
						v-if="showDiscover"
						:label="discoverEvents.shortLabel"
						:icon="discoverEvents.icon"
						@click="openDiscoverEvents"
					/>
				</MobileNav>
			</Transition>
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
