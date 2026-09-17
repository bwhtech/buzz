<script setup lang="ts">
import { ErrorMessage, Icon, Skeleton } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import EmptyState from "@/components/common/EmptyState.vue"
import SectionHeader from "@/components/common/SectionHeader.vue"
import EventArchivedAlert from "@/components/dashboard/events/EventArchivedAlert.vue"
import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import AddSponsorDialog from "@/components/dashboard/sponsorships/AddSponsorDialog.vue"
import EnquiriesSection from "@/components/dashboard/sponsorships/EnquiriesSection.vue"
import EnquiryDrawer from "@/components/dashboard/sponsorships/EnquiryDrawer.vue"
import EventSponsorshipActions from "@/components/dashboard/sponsorships/EventSponsorshipActions.vue"
import SponsorCard from "@/components/dashboard/sponsorships/SponsorCard.vue"
import SponsorDrawer from "@/components/dashboard/sponsorships/SponsorDrawer.vue"
import TierCard from "@/components/dashboard/sponsorships/TierCard.vue"
import TierDialog from "@/components/dashboard/sponsorships/TierDialog.vue"
import TierDrawer from "@/components/dashboard/sponsorships/TierDrawer.vue"
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
	const rank = new Map((page.data?.tiers ?? []).map((tier) => [tier.name, tier.price]))
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

const message = (error: unknown) => (error as FrappeError | null)?.messages?.join("\n")
</script>

<template>
	<EventPageHeader :title="page.data?.title" section="Sponsorships" />

	<PageWithSidebar>
		<EventArchivedAlert :event="eventId" />

		<div v-if="page.loading" class="space-y-8">
			<Skeleton class="h-6 w-24" />
			<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
				<Skeleton v-for="row in 3" :key="row" class="h-28 w-full rounded-4" />
			</div>
		</div>

		<ErrorMessage v-else-if="page.error" :message="message(page.error)" />

		<template v-else>
			<section class="space-y-3">
				<SectionHeader title="Tiers" :count="page.data?.tiers.length" :action="addTierAction" />

				<div v-if="page.data?.tiers.length" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
					<TierCard
						v-for="tier in page.data.tiers"
						:key="tier.name"
						:tier="tier"
						:can-write="page.data.can_write"
						@open="select('tier', tier.name)"
					/>
				</div>
				<EmptyState
					v-else
					title="No tiers yet"
					description="Tiers set the sponsorship packages and prices applicants choose from."
				>
					<template #illustration>
						<Icon name="lucide-layers" class="size-5 text-ink-gray-5" />
					</template>
				</EmptyState>
			</section>

			<section class="space-y-3">
				<SectionHeader
					title="Sponsors"
					:count="page.data?.sponsors.length"
					:action="addSponsorAction"
				/>

				<div v-if="sponsors.length" class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
					<SponsorCard
						v-for="sponsor in sponsors"
						:key="sponsor.name"
						:sponsor="sponsor"
						@open="select('sponsor', sponsor.name)"
					/>
				</div>
				<EmptyState
					v-else
					title="No sponsors yet"
					description="Sponsors appear here once they pay or are confirmed by the team."
				>
					<template #illustration>
						<Icon name="lucide-handshake" class="size-5 text-ink-gray-5" />
					</template>
				</EmptyState>
			</section>

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

	<TierDialog v-model="tierDialogOpen" :event="eventId" @saved="page.reload()" />
</template>
