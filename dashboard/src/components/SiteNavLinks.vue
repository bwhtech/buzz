<script setup lang="ts">
import { Button, Dropdown } from "frappe-ui"

import type { NavbarLink } from "@/types"
import { linkTarget, menuOption } from "@/utils/navbar"

defineProps<{ links: NavbarLink[]; align: "start" | "end" }>()

// Anchors, not Buttons: frappe-ui's Button opens every link in a new tab.
const linkClass =
	"inline-flex h-8 items-center rounded-4 px-2.5 text-base-medium text-ink-gray-8 transition-colors hover:bg-surface-gray-3 active:bg-surface-gray-4 focus-visible:outline-none focus-visible:focus-ring"
</script>

<template>
	<!-- Small screens get these links from SiteHeader's menu button instead. -->
	<nav v-if="links.length" class="hidden items-center gap-1 sm:flex">
		<template v-for="link in links" :key="link.label">
			<Dropdown
				v-if="link.child_items.length"
				:options="link.child_items.map(menuOption)"
				:align="align"
			>
				<Button variant="ghost" size="md" :label="link.label" icon-right="lucide-chevron-down" />
			</Dropdown>
			<a
				v-else-if="link.url"
				:href="link.url"
				:target="linkTarget(link)"
				:rel="linkTarget(link) && 'noopener'"
				:class="linkClass"
			>
				{{ link.label }}
			</a>
		</template>
	</nav>
</template>
