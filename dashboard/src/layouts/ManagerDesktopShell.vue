<script setup lang="ts">
import { DesktopShell, Divider, PageHeaderTarget, Sidebar, SidebarItem, Skeleton } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { useRoute } from "vue-router"

import ManagerSidebarHeader from "@/components/dashboard/ManagerSidebarHeader.vue"
import WorkspaceOpening from "@/components/dashboard/WorkspaceOpening.vue"
import UserMenu from "@/components/UserMenu.vue"
import { openingTeam } from "@/composables/useWorkspaceOpening"
import {
	discoverEvents,
	openDiscoverEvents,
	type ManagerNavItem,
	type Workspace,
} from "@/utils/managerNavigation"

const props = defineProps<{ items: ManagerNavItem[]; workspace?: Workspace }>()

const route = useRoute()

// Events, Submissions, Members, Payments and Settings.
const WORKSPACE_ITEM_COUNT = 5

// SidebarItem infers this from `to` on paper, but its `active` prop is declared
// type Boolean, so Vue casts the absent prop to false and the inference never runs.
const isActive = (to: string) => route.path === to

// The header swaps between the brand mark, an event or team, and the create-event way out.
const headerKey = computed(() => {
	if (route.name === "create-event") return "create"
	return props.workspace ? "workspace" : "root"
})

// Leaving the root pushes the sidebar left, returning to it pulls back right.
const direction = ref<"forward" | "back">("forward")
watch(headerKey, (key, previous) => {
	direction.value = previous === "root" && key !== "root" ? "forward" : "back"
})
</script>

<template>
	<!-- scroll=false: the rounded panel below owns its own scroll. -->
	<DesktopShell :scroll="false">
		<template #sidebar>
			<Sidebar>
				<!-- px-1: puts the header mark on the item-icon centerline, in every state.
				     h-14 holds the height while two states overlap mid-transition. -->
				<div class="nav-stage relative h-14 shrink-0">
					<Transition :name="`nav-${direction}`">
						<div :key="headerKey" class="absolute inset-x-1 top-2 flex items-center">
							<ManagerSidebarHeader :workspace="workspace" />
						</div>
					</Transition>
				</div>

				<!-- One block, not per row: absolute rows would all collapse onto the
				     container's corner. my-2, not py-2: the leaving list anchors to the
				     padding box, so padding here would lift it out of line. -->
				<div class="nav-stage relative mx-2 my-2">
					<Transition :name="`nav-${direction}`">
						<div :key="headerKey" class="nav-list flex flex-col gap-0.5">
							<!-- Stands in for the workspace destinations while it opens. -->
							<template v-if="openingTeam">
								<div
									v-for="row in WORKSPACE_ITEM_COUNT"
									:key="row"
									class="flex h-7 items-center gap-2 px-2"
									aria-hidden="true"
								>
									<Skeleton class="size-4 rounded-2" />
									<Skeleton class="h-3 w-24 rounded-2" />
								</div>
							</template>
							<template v-for="item in items" v-else :key="item.label">
								<Divider v-if="item.startsGroup" class="my-1.5" />
								<SidebarItem
									:label="item.label"
									:icon="item.icon"
									:to="item.to"
									:active="isActive(item.to)"
								/>
							</template>
						</div>
					</Transition>
				</div>

				<div class="mt-auto flex flex-col gap-2 px-2 py-2">
					<SidebarItem
						:label="discoverEvents.label"
						:icon="discoverEvents.icon"
						:on-click="openDiscoverEvents"
					>
						<template #suffix>
							<span class="lucide-arrow-up-right mr-2 size-3.5 text-ink-gray-4" />
						</template>
					</SidebarItem>
					<UserMenu />
				</div>
			</Sidebar>
		</template>

		<div class="flex flex-col h-full min-h-0 bg-surface-sidebar py-2 pl-1">
			<div
				class="relative flex h-full flex-col overflow-hidden rounded-l-6 bg-surface-elevation-1 shadow-base"
			>
				<PageHeaderTarget />
				<div class="relative min-h-0 flex-1 overflow-y-auto">
					<router-view />
				</div>
				<WorkspaceOpening />
			</div>
		</div>
	</DesktopShell>
</template>

<style scoped>
/* One vanishing point per stage, so header and list hinge off the same rail. */
.nav-stage {
	perspective: 700px;
}

.nav-forward-enter-active,
.nav-back-enter-active,
.nav-forward-leave-active,
.nav-back-leave-active {
	transform-origin: left center;
}

/* Opacity lands before the movement: a row still visible at the end of its slide
   reads as a ghost. */
.nav-forward-enter-active,
.nav-back-enter-active {
	transition:
		opacity 140ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}

.nav-forward-leave-active,
.nav-back-leave-active {
	transition:
		opacity 100ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 140ms cubic-bezier(0.23, 1, 0.32, 1);
}

/* Only the list leaves the flow; re-anchoring the header would shift it 4px. */
.nav-list.nav-forward-leave-active,
.nav-list.nav-back-leave-active {
	position: absolute;
	inset-inline: 0;
	top: 0;
}

.nav-forward-enter-from,
.nav-back-leave-to {
	opacity: 0;
	transform: translateX(10px) rotateY(-8deg);
}

.nav-forward-leave-to,
.nav-back-enter-from {
	opacity: 0;
	transform: translateX(-10px) rotateY(8deg);
}

@media (prefers-reduced-motion: reduce) {
	.nav-forward-enter-from,
	.nav-forward-leave-to,
	.nav-back-enter-from,
	.nav-back-leave-to {
		transform: none;
	}
}
</style>
