<script setup lang="ts">
import { ErrorMessage, Skeleton } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import ListSection from "@/components/common/ListSection.vue"
import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import AddPricedItemDialog from "@/components/dashboard/sponsorships/AddPricedItemDialog.vue"
import AddSponsorDialog from "@/components/dashboard/sponsorships/AddSponsorDialog.vue"
import EnquiriesSection from "@/components/dashboard/sponsorships/EnquiriesSection.vue"
import EnquiryDrawer from "@/components/dashboard/sponsorships/EnquiryDrawer.vue"
import EventSponsorshipActions from "@/components/dashboard/sponsorships/EventSponsorshipActions.vue"
import SponsorDrawer from "@/components/dashboard/sponsorships/SponsorDrawer.vue"
import SponsorsSection from "@/components/dashboard/sponsorships/SponsorsSection.vue"
import TierDrawer from "@/components/dashboard/sponsorships/TierDrawer.vue"
import TierList from "@/components/dashboard/sponsorships/TierList.vue"
import { useEventSponsorships } from "@/data/sponsorships"
import PageWithSidebar from "@/layouts/PageWithSidebar.vue"
import type { FrappeError } from "@/types"

const route = useRoute()
const eventId = route.params.eventId as string

const page = useEventSponsorships(eventId)

const tierDialogOpen = ref(false)

const addTierAction = computed(() =>
	page.data?.can_write
		? {
				label: "Add Tier",
				variant: "outline" as const,
				iconLeft: "lucide-plus",
				onClick: openTierDialog,
			}
		: null,
)

const sponsorDialogOpen = ref(false)

function openSponsorDialog() {
	sponsorDialogOpen.value = true
}

const addSponsorAction = computed(() =>
	page.data?.can_write
		? {
				label: "Add Manually",
				variant: "outline" as const,
				iconLeft: "lucide-plus",
				onClick: openSponsorDialog,
			}
		: null,
)

function openTierDialog() {
	tierDialogOpen.value = true
}

// One drawer at a time: the item is held by name so a reload keeps it pointing at fresh data.
type Selection = { kind: "tier" | "sponsor" | "enquiry"; name: string }
const selected = ref<Selection | null>(null)

const select = (kind: Selection["kind"], name: string) => (selected.value = { kind, name })

function pick<T extends { name: string }>(kind: Selection["kind"], rows: T[] | undefined) {
	if (selected.value?.kind !== kind) return null
	return rows?.find((row) => row.name === selected.value?.name) ?? null
}

const selectedTier = computed(() => pick("tier", page.data?.tiers))
const selectedSponsor = computed(() => pick("sponsor", page.data?.sponsors))
const selectedEnquiry = computed(() =>
	selected.value?.kind === "enquiry" ? selected.value.name : null,
)

function drawerOpen(kind: Selection["kind"]) {
	return computed<boolean>({
		get: () => selected.value?.kind === kind,
		set: (open) => !open && (selected.value = null),
	})
}

const enquiriesSection = ref<InstanceType<typeof EnquiriesSection> | null>(null)
const sponsorsSection = ref<InstanceType<typeof SponsorsSection> | null>(null)

// The row is patched in place; the page reloads for the counts and any sponsor a payment added.
function onEnquiryStatusChanged(status: string) {
	if (selectedEnquiry.value) enquiriesSection.value?.applyStatus(selectedEnquiry.value, status)
	page.reload()
}

// Removing a sponsor cancels the enquiry it came from, so that list is stale too.
function onSponsorsChanged() {
	page.reload()
	sponsorsSection.value?.reload()
	enquiriesSection.value?.reload()
}

function onSponsorTagged() {
	page.reload()
	sponsorsSection.value?.reload()
}

const tierDrawerOpen = drawerOpen("tier")
const sponsorDrawerOpen = drawerOpen("sponsor")
const enquiryDrawerOpen = drawerOpen("enquiry")

const message = (error: unknown) => (error as FrappeError | null)?.message
</script>

<template>
	<EventPageHeader :title="page.data?.title" section="Sponsorships" />

	<PageWithSidebar>
		<EventArchivedAlert :event="eventId" />

		<div v-if="page.loading && !page.data" class="space-y-8">
			<Skeleton class="h-6 w-24" />
			<Skeleton class="h-48 w-full rounded-4" />
		</div>

		<ErrorMessage v-else-if="page.error" :message="message(page.error)" />

		<template v-else>
			<ListSection
				title="Tiers"
				:count="page.data?.tiers.length"
				:action="addTierAction"
				:empty="!page.data?.tiers.length"
				empty-title="No tiers yet"
				empty-description="Tiers set the sponsorship packages and prices applicants choose from."
				empty-icon="lucide-layers"
			>
				<TierList
					v-if="page.data"
					:tiers="page.data.tiers"
					:can-write="page.data.can_write"
					@open="select('tier', $event)"
				/>
			</ListSection>

			<SponsorsSection
				ref="sponsorsSection"
				:event="eventId"
				:tiers="page.data?.tiers ?? []"
				:action="addSponsorAction"
				@open="select('sponsor', $event)"
			/>

			<EnquiriesSection ref="enquiriesSection" :event="eventId" @open="select('enquiry', $event)" />
		</template>

		<template v-if="page.data?.form" #sidebar>
			<EventSponsorshipActions
				:form="page.data.form"
				:can-write="!!page.data.can_write"
				@changed="page.reload()"
			/>
		</template>
	</PageWithSidebar>

	<TierDrawer
		v-model:open="tierDrawerOpen"
		:tier="selectedTier"
		:sponsors="page.data?.sponsors ?? []"
		:can-write="!!page.data?.can_write"
		@changed="page.reload()"
		@open-sponsor="select('sponsor', $event)"
	/>

	<SponsorDrawer
		v-model:open="sponsorDrawerOpen"
		:sponsor="selectedSponsor"
		:tiers="page.data?.tiers ?? []"
		:team="page.data?.team ?? ''"
		:tags="page.data?.tags ?? []"
		:can-write="!!page.data?.can_write"
		@changed="onSponsorsChanged"
		@tagged="onSponsorTagged"
		@open-enquiry="select('enquiry', $event)"
	/>

	<EnquiryDrawer
		v-model:open="enquiryDrawerOpen"
		:enquiry="selectedEnquiry"
		:can-write="!!page.data?.can_write"
		@changed="onEnquiryStatusChanged"
		@open-sponsor="select('sponsor', $event)"
	/>

	<AddSponsorDialog
		v-model="sponsorDialogOpen"
		:event="eventId"
		:tiers="page.data?.tiers ?? []"
		@added="onSponsorsChanged"
	/>

	<AddPricedItemDialog
		v-model="tierDialogOpen"
		:event="eventId"
		doctype="Sponsorship Tier"
		item-label="Tier"
		placeholder="Gold"
		@saved="page.reload()"
	/>
</template>
