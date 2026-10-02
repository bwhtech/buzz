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
import SponsorCard from "@/components/dashboard/sponsorships/SponsorCard.vue"
import SponsorDrawer from "@/components/dashboard/sponsorships/SponsorDrawer.vue"
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

// Highest-priced tier first, the order a sponsor wall reads in.
const sponsors = computed(() => {
	const rank = new Map((page.data?.tiers ?? []).map((tier) => [tier.name, tier.prices[0].price]))
	return (page.data?.sponsors ?? []).toSorted(
		(a, b) => (rank.get(b.tier ?? "") ?? 0) - (rank.get(a.tier ?? "") ?? 0),
	)
})

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

// The row is patched in place; the page reloads for the counts and any sponsor a payment added.
function onEnquiryStatusChanged(status: string) {
	if (selectedEnquiry.value) enquiriesSection.value?.applyStatus(selectedEnquiry.value, status)
	page.reload()
}

// Removing a sponsor cancels the enquiry it came from, so that list is stale too.
function onSponsorsChanged() {
	page.reload()
	enquiriesSection.value?.reload()
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

		<div v-if="page.loading" class="space-y-8">
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

			<ListSection
				title="Sponsors"
				:count="page.data?.sponsors.length"
				:action="addSponsorAction"
				:empty="!sponsors.length"
				empty-title="No sponsors yet"
				empty-description="Sponsors appear here once they pay or are confirmed by the team."
				empty-icon="lucide-handshake"
			>
				<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
					<SponsorCard
						v-for="sponsor in sponsors"
						:key="sponsor.name"
						:sponsor="sponsor"
						@open="select('sponsor', sponsor.name)"
					/>
				</div>
			</ListSection>

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
		:can-write="!!page.data?.can_write"
		@changed="onSponsorsChanged"
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
