<script setup lang="ts">
import { Breadcrumbs, Button, PageHeader, PageHeaderMobile } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import EventHeaderActions from "@/components/dashboard/events/EventHeaderActions.vue"
import NotificationsButton from "@/components/dashboard/notifications/NotificationsButton.vue"
import { useIsMobile } from "@/composables/useIsMobile"

// The event, then the section of it being looked at. Neither crumb is a link: the
// event on its own resolves to whichever section is open. A page with its own big
// heading hides the crumbs until that heading scrolls away.
const props = defineProps<{
	title: string | null | undefined
	section: string
	modified?: string | null
	dirty?: boolean
	hideCrumbs?: boolean
}>()

const isMobile = useIsMobile()
const route = useRoute()

const items = computed(() => [{ label: props.title || "Event" }, { label: props.section }])
</script>

<template>
	<template v-if="isMobile">
		<PageHeaderMobile :title="title ?? ''">
			<template #prefix>
				<slot name="leading">
					<!-- Not history back: every tab tap pushes a history entry. -->
					<Button
						variant="ghost"
						icon="lucide-chevron-left"
						label="Back to events"
						:route="{ name: 'events' }"
					/>
				</slot>
			</template>
			<template #suffix>
				<slot />
				<!-- Save and Discard need the room while there are unsaved edits. -->
				<NotificationsButton v-if="!dirty" />
			</template>
		</PageHeaderMobile>
		<EventArchivedAlert :event="route.params.eventId as string" banner />
	</template>

	<PageHeader v-else class="border-none pt-2 bg-surface-elevation-1">
		<div
			class="header-crumb min-w-0"
			:data-hidden="hideCrumbs || undefined"
			:aria-hidden="hideCrumbs"
		>
			<Breadcrumbs :items="items" />
		</div>
		<div class="flex shrink-0 items-center gap-2">
			<EventHeaderActions :modified="modified" />
			<slot name="leading" />
			<slot />
		</div>
	</PageHeader>
</template>

<style scoped>
/* Entering is slower than leaving: the eye is looking for it on the way in. */
.header-crumb {
	transition:
		opacity 240ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 240ms cubic-bezier(0.23, 1, 0.32, 1);
}
.header-crumb[data-hidden] {
	opacity: 0;
	transform: translateY(8px);
	pointer-events: none;
	transition-duration: 160ms;
}
@media (prefers-reduced-motion: reduce) {
	.header-crumb {
		transform: none !important;
	}
}
</style>
