<script setup lang="ts">
import { MobileNav, MobileNavItem, MobileShell } from "frappe-ui"
import { useRoute } from "vue-router"

import { discoverEvents, openDiscoverEvents, type ManagerNavItem } from "@/utils/managerNavigation"

defineProps<{ items: ManagerNavItem[]; showDiscover?: boolean }>()

// `active` is a Boolean prop, so leaving it unset casts to false and skips route matching.
const route = useRoute()
</script>

<template>
	<MobileShell>
		<div class="min-h-full bg-surface-elevation-1">
			<router-view />
		</div>

		<template #nav>
			<MobileNav v-if="items.length">
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
		</template>
	</MobileShell>
</template>
