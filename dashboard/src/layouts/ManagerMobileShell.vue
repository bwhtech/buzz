<script setup lang="ts">
import { MobileNav, MobileNavItem, MobileShell } from "frappe-ui"
import { useRoute } from "vue-router"

import type { ManagerNavItem } from "@/utils/managerNavigation"

defineProps<{ items: ManagerNavItem[] }>()

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
			</MobileNav>
		</template>
	</MobileShell>
</template>
