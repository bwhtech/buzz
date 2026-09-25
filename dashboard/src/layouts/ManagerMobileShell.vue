<script setup lang="ts">
import { MobileNav, MobileNavItem, MobileShell } from "frappe-ui"

import UserMenu from "@/components/UserMenu.vue"
import type { ManagerNavItem } from "@/utils/managerNavigation"

defineProps<{ items: ManagerNavItem[]; eventId?: string }>()
</script>

<template>
	<MobileShell>
		<!-- The pages paint their headers and rules on elevation-1, as in the desktop panel. -->
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
				/>
				<!-- An event's six sections fill the bar; the account waits one level up. -->
				<UserMenu v-if="!eventId" variant="tab" />
			</MobileNav>
		</template>
	</MobileShell>
</template>
