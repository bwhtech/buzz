import { ref } from "vue"

import type { NavbarLink } from "@/types"

// Set by pages that draw their own header, such as the booking form.
export const siteHeaderHidden = ref(false)

export const linkTarget = (link: NavbarLink) => (link.open_in_new_tab ? "_blank" : undefined)

export const menuOption = (link: NavbarLink) => ({
	label: link.label,
	onClick: () => window.open(link.url ?? "/", linkTarget(link) ?? "_self"),
})

// Every top bar link in one menu: plain links first, then each dropdown as a labelled group.
export function mobileMenu(links: NavbarLink[]) {
	const plain = links.filter((link) => !link.child_items.length && link.url)
	const groups = links
		.filter((link) => link.child_items.length)
		.map((link) => ({ group: link.label, options: link.child_items.map(menuOption) }))
	return [{ group: "", hideLabel: true, options: plain.map(menuOption) }, ...groups]
}
