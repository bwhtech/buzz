// Trigger, Close, Title and Description carry no styling of their own — pass `as-child`
// or a class and let the caller decide — so they come straight from reka. Title and
// Description also wire the content's aria-labelledby and aria-describedby, so a drawer
// should always render them even when its layout puts them somewhere unusual.
export { DrawerClose, DrawerDescription, DrawerTitle, DrawerTrigger } from "reka-ui"

export { default as Drawer } from "./Drawer.vue"
export { default as DrawerContent } from "./DrawerContent.vue"
