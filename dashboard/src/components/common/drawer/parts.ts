import {
	DialogClose,
	DialogDescription,
	DialogTitle,
	DrawerClose as RekaDrawerClose,
	DrawerDescription as RekaDrawerDescription,
	DrawerTitle as RekaDrawerTitle,
} from "reka-ui"
import { type Component, defineComponent, h } from "vue"

import { useIsMobile } from "@/composables/useIsMobile"

// Mobile drawers are BottomSheets (reka Dialog), so parts must match the open root.
function responsivePart(drawerPart: Component, sheetPart: Component) {
	return defineComponent({
		inheritAttrs: false,
		setup(_, { attrs, slots }) {
			const isMobile = useIsMobile()
			return () => h(isMobile.value ? sheetPart : drawerPart, attrs, slots)
		},
	})
}

export const DrawerClose = responsivePart(RekaDrawerClose, DialogClose)
export const DrawerTitle = responsivePart(RekaDrawerTitle, DialogTitle)
export const DrawerDescription = responsivePart(RekaDrawerDescription, DialogDescription)
