<script setup lang="ts">
import { DrawerContent, DrawerHandle, DrawerOverlay, DrawerPortal } from "reka-ui"

withDefaults(
	defineProps<{
		showSwipeHandle?: boolean
		// Governs the cross axis: width for a side drawer, height for a bottom or top one.
		size?: "md" | "lg" | "xl"
	}>(),
	{ showSwipeHandle: true, size: "md" },
)
</script>

<template>
	<DrawerPortal>
		<DrawerOverlay class="drawer-overlay fixed inset-0 z-40 bg-black/20 backdrop-blur-sm" />

		<DrawerContent :data-size="size" class="drawer bg-surface-elevation-2 shadow-2xl">
			<DrawerHandle
				v-if="showSwipeHandle"
				class="drawer-handle mx-auto my-3 h-1.5 w-12 shrink-0 rounded-full bg-surface-gray-4"
			/>
			<slot />

			<!-- reka has no footer part and shadcn's is a plain styled div, so this is the
			     same idea as a slot: pinned below the body, never scrolling with it. -->
			<div v-if="$slots.footer" class="mt-auto flex shrink-0 items-center gap-2 p-4">
				<slot name="footer" />
			</div>
		</DrawerContent>
	</DrawerPortal>
</template>

<style scoped>
/* reka positions nothing: it sets data-swipe-direction plus the swipe offset vars and
   leaves the transform to us, the same contract Base UI gives shadcn.

   Keyframes rather than transitions, against the usual preference: reka's Presence
   decides when to unmount by waiting for animationend and reading animation-name, so a
   plain transition unmounts instantly with no exit. Keyframes also give an entrance,
   which a transition cannot — the element mounts already at data-state="open", with no
   from-state to travel from. */
.drawer {
	position: fixed;
	z-index: 50;
	display: flex;
	flex-direction: column;
	overflow: hidden;
	--drawer-inset: 0.5rem;
	--drawer-width: 28rem;
	--drawer-height: calc(100dvh - 12rem);
	--ease-out: cubic-bezier(0.23, 1, 0.32, 1);
}

.drawer[data-state="open"] {
	animation: drawer-in 320ms var(--ease-out);
}
/* Fast where the system responds, slower where the user was deciding. */
.drawer[data-state="closed"] {
	animation: drawer-out 200ms var(--ease-out) forwards;
}

/* Following the finger has to be instant, or the drawer lags behind the drag. */
.drawer[data-swiping] {
	animation: none;
}

@keyframes drawer-in {
	from {
		transform: var(--drawer-hidden);
	}
}
@keyframes drawer-out {
	to {
		transform: var(--drawer-hidden);
	}
}

/* The largest takes half the viewport once there is room for it; below that the 75%
   cross-axis rule already keeps it from swallowing a small screen. */
.drawer[data-size="lg"] {
	--drawer-width: 36rem;
	--drawer-height: calc(100dvh - 6rem);
}
.drawer[data-size="xl"] {
	--drawer-width: max(28rem, 50vw);
	--drawer-height: max(28rem, 50dvh);
}

.drawer[data-swipe-direction="down"],
.drawer[data-swipe-direction="up"] {
	left: 0;
	right: 0;
	max-height: var(--drawer-height);
	transform: translateY(var(--drawer-swipe-movement-y, 0px));
}

/* Inset from every edge rather than pinned to one: a side drawer reads as a panel over
   the page, so it keeps its rounding on all four corners. */
.drawer[data-swipe-direction="left"],
.drawer[data-swipe-direction="right"] {
	top: var(--drawer-inset);
	bottom: var(--drawer-inset);
	width: 75%;
	max-width: var(--drawer-width);
	border-radius: var(--radius-6);
	transform: translateX(var(--drawer-swipe-movement-x, 0px));
}

/* The inset has to be travelled too, or the drawer parks a gap short of the edge. */
.drawer[data-swipe-direction="down"] {
	bottom: 0;
	border-top-left-radius: var(--radius-6);
	border-top-right-radius: var(--radius-6);
	--drawer-hidden: translateY(100%);
}
.drawer[data-swipe-direction="up"] {
	top: 0;
	border-bottom-left-radius: var(--radius-6);
	border-bottom-right-radius: var(--radius-6);
	--drawer-hidden: translateY(-100%);
}
.drawer[data-swipe-direction="left"] {
	left: var(--drawer-inset);
	--drawer-hidden: translateX(calc(-100% - var(--drawer-inset)));
}
.drawer[data-swipe-direction="right"] {
	right: var(--drawer-inset);
	--drawer-hidden: translateX(calc(100% + var(--drawer-inset)));
}

/* A side drawer has no edge to swipe down from, so its handle would be a lie. */
.drawer[data-swipe-direction="left"] .drawer-handle,
.drawer[data-swipe-direction="right"] .drawer-handle {
	display: none;
}

/* Settled before the panel lands rather than racing it. */
.drawer-overlay {
	--ease-out: cubic-bezier(0.23, 1, 0.32, 1);
}
.drawer-overlay[data-state="open"] {
	animation: drawer-overlay-in 240ms var(--ease-out);
}
.drawer-overlay[data-state="closed"] {
	animation: drawer-overlay-out 200ms var(--ease-out) forwards;
}

@keyframes drawer-overlay-in {
	from {
		opacity: 0;
	}
}
@keyframes drawer-overlay-out {
	to {
		opacity: 0;
	}
}

/* Gentler, not none: the fade still explains what happened, nothing travels. */
@media (prefers-reduced-motion: reduce) {
	.drawer[data-state="open"] {
		animation: drawer-overlay-in 200ms var(--ease-out);
	}
	.drawer[data-state="closed"] {
		animation: drawer-overlay-out 200ms var(--ease-out) forwards;
	}
}
</style>
