<script setup lang="ts">
import { Button, Dropdown } from "frappe-ui"

import type { NavbarLink } from "@/types"

defineProps<{ links: NavbarLink[]; align: "start" | "end" }>()

// Anchors, not Buttons: frappe-ui's Button opens every link in a new tab.
const linkClass =
	"inline-flex h-8 items-center rounded-4 px-2.5 text-base-medium text-ink-gray-8 transition-colors hover:bg-surface-gray-3 active:bg-surface-gray-4 focus-visible:outline-none focus-visible:focus-ring"

const target = (link: NavbarLink) => (link.open_in_new_tab ? "_blank" : undefined)

const menuOptions = (link: NavbarLink) =>
	link.child_items.map((child) => ({
		label: child.label,
		onClick: () => window.open(child.url ?? "/", target(child) ?? "_self"),
	}))
</script>

<template>
	<!-- No mobile menu yet: the top bar links hide on small screens. -->
	<nav v-if="links.length" class="hidden items-center gap-1 sm:flex">
		<template v-for="link in links" :key="link.label">
			<Dropdown v-if="link.child_items.length" :options="menuOptions(link)" :align="align">
				<Button variant="ghost" size="md" :label="link.label" icon-right="lucide-chevron-down" />
			</Dropdown>
			<a
				v-else-if="link.url"
				:href="link.url"
				:target="target(link)"
				:rel="target(link) && 'noopener'"
				:class="linkClass"
			>
				{{ link.label }}
			</a>
		</template>
	</nav>
</template>
