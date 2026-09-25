// Title and Description wire aria-labelledby and aria-describedby, so a drawer should
// always render them even when its layout puts them somewhere unusual.
export { DrawerTrigger } from "reka-ui"
export { DrawerClose, DrawerDescription, DrawerTitle } from "./parts"

export { default as Drawer } from "./Drawer.vue"
export { default as DrawerContent } from "./DrawerContent.vue"
export { default as DrawerCloseButton } from "./DrawerCloseButton.vue"
