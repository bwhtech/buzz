<script setup lang="ts">
import {
	Breadcrumbs,
	Button,
	PageHeader,
	PageHeaderBase,
	PageHeaderMobile,
	PageHeaderMobileTitle,
	Tooltip,
	dayjsLocal,
} from "frappe-ui"
import { computed } from "vue"

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

const items = computed(() => [{ label: props.title || "Event" }, { label: props.section }])

const modifiedAt = computed(() => (props.modified ? dayjsLocal(props.modified) : null))
const modifiedRelative = computed(() => modifiedAt.value?.fromNow() ?? "")
const modifiedExact = computed(() => modifiedAt.value?.format("D MMM YYYY, h:mm A") ?? "")
</script>

<template>
	<template v-if="isMobile">
		<!-- The tab bar already names the section, so the title carries the event. -->
		<PageHeaderMobile>
			<template #prefix>
				<Button
					variant="ghost"
					icon="lucide-chevron-left"
					label="Back to events"
					:route="{ name: 'events' }"
				/>
			</template>
			<PageHeaderMobileTitle :title="title || section" />
		</PageHeaderMobile>
		<!-- Page actions get a strip of their own: a centered title leaves them a third of
		     the width. empty: drops the strip while a v-if inside the slot renders nothing. -->
		<PageHeaderBase class="flex justify-end gap-2 border-b bg-surface-base px-3 py-2 empty:hidden">
			<slot />
		</PageHeaderBase>
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
			<slot />
		</div>
	</PageHeader>
</template>
