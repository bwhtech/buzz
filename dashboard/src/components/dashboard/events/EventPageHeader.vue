<script setup lang="ts">
import { Breadcrumbs, Button, PageHeader, PageHeaderMobile, Tooltip, dayjsLocal } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import { useIsMobile } from "@/composables/useIsMobile"

// The event, then the section of it being looked at. Neither crumb is a link: the
// event on its own resolves to whichever section is open. Modified arrives as the
// raw timestamp and renders relative, with the exact date on hover — the same
// shape as ProposalCard's "last updated" readout.
const props = defineProps<{
	title: string | null | undefined
	section: string
	modified?: string | null
}>()

const isMobile = useIsMobile()
const route = useRoute()

const items = computed(() => [{ label: props.title || "Event" }, { label: props.section }])

const modifiedAt = computed(() => (props.modified ? dayjsLocal(props.modified) : null))
const modifiedRelative = computed(() => modifiedAt.value?.fromNow() ?? "")
const modifiedExact = computed(() => modifiedAt.value?.format("D MMM YYYY, h:mm A") ?? "")
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
			</template>
		</PageHeaderMobile>
		<EventArchivedAlert :event="route.params.eventId as string" banner />
	</template>

	<PageHeader v-else class="border-none pt-2 bg-surface-elevation-1">
		<Breadcrumbs :items="items" />
		<div class="flex items-center gap-2">
			<Tooltip v-if="modifiedAt" :text="`Last updated on ${modifiedExact}`">
				<span class="flex items-center gap-1 text-p-sm text-ink-gray-4">
					<span class="lucide-clock-fading size-3.5 shrink-0" aria-hidden="true" />
					Modified {{ modifiedRelative }}
				</span>
			</Tooltip>
			<slot name="leading" />
			<slot />
		</div>
	</PageHeader>
</template>
