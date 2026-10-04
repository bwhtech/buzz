<script setup lang="ts">
import { Alert, FormControl, toast, useDoc } from "frappe-ui"
import { computed } from "vue"

import DrawerSaveBar from "@/components/dashboard/sponsorships/DrawerSaveBar.vue"
import { keepLastValue } from "@/components/dashboard/sponsorships/helpers"
import PerkList from "@/components/dashboard/sponsorships/PerkList.vue"
import PriceList from "@/components/dashboard/sponsorships/PriceList.vue"
import SponsorCard from "@/components/dashboard/sponsorships/SponsorCard.vue"
import SponsorshipDrawer from "@/components/dashboard/sponsorships/SponsorshipDrawer.vue"
import { useDrawerEdits } from "@/composables/useDrawerEdits"
import type { EventSponsorItem, SponsorshipTierItem, TierPrice } from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"

type TierValues = {
	title: string
	prices: TierPrice[]
	slots: number
	perks: string[]
}
type TierDoc = Pick<TierValues, "title" | "prices" | "slots"> & {
	name: string
	enabled: 0 | 1
	perks: string
}

const props = defineProps<{
	tier: SponsorshipTierItem | null
	sponsors: EventSponsorItem[]
	canWrite: boolean
}>()
const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ changed: []; openSponsor: [name: string] }>()

const shownTier = keepLastValue(() => props.tier)

const tierDoc = useDoc<TierDoc>({
	doctype: "Sponsorship Tier",
	name: () => props.tier?.name ?? "",
	immediate: false,
})

const { draft, hasChanges, discardChanges, confirmAndSave } = useDrawerEdits<TierValues>(
	() => props.tier?.name,
	() => props.tier && toTierValues(props.tier),
	save,
	{
		title: "Save tier",
		message: "Applicants and existing enquiries will see the updated tier.",
		success: "Tier updated",
	},
)

const isInvalid = computed(
	() =>
		!draft.value.title?.trim() ||
		draft.value.prices?.some((row) => !row.currency || !(row.price >= 0)),
)

const sponsorsInTier = computed(() => props.sponsors.filter((row) => row.tier === props.tier?.name))

const formattedPrice = computed(() => {
	const defaultPrice = props.tier?.prices[0]
	return defaultPrice ? formatWholePriceOrFree(defaultPrice.price, defaultPrice.currency) : ""
})

const enabledAlert = computed(() =>
	props.tier?.enabled
		? { theme: "green" as const, title: "Tier is Enabled", action: "Disable" }
		: { theme: "amber" as const, title: "Tier is Disabled", action: "Enable" },
)

async function toggleEnabled() {
	if (!props.tier) return
	const enabling = !props.tier.enabled
	await tierDoc.setValue.submit({ enabled: enabling ? 1 : 0 })
	if (tierDoc.setValue.error) {
		toast.error("Could not update the tier. Try again.")
		return
	}
	toast.success(enabling ? "Tier enabled" : "Tier disabled")
	emit("changed")
}

// Perks are stored one per line; the drawer edits them as a list.
function toTierValues(tier: SponsorshipTierItem): TierValues {
	return {
		title: tier.title,
		prices: tier.prices.map((row) => ({ ...row })),
		slots: tier.slots,
		perks: (tier.perks ?? "").split("\n").filter((perk) => perk.trim()),
	}
}

async function save(values: TierValues) {
	await tierDoc.setValue.submit({
		title: values.title.trim(),
		prices: values.prices,
		slots: values.slots,
		perks: values.perks
			.map((perk) => perk.trim())
			.filter(Boolean)
			.join("\n"),
	})
	if (tierDoc.setValue.error) throw tierDoc.setValue.error
	emit("changed")
}
</script>

<template>
	<SponsorshipDrawer
		v-if="shownTier"
		v-model:open="open"
		:title="shownTier.title"
		:description="formattedPrice"
	>
		<template #notice>
			<Alert
				:theme="enabledAlert.theme"
				:title="enabledAlert.title"
				:primary-action="
					canWrite
						? {
								label: enabledAlert.action,
								variant: 'outline',
								theme: 'gray',
								loading: tierDoc.setValue.loading,
								onClick: toggleEnabled,
							}
						: undefined
				"
			/>
		</template>

		<form novalidate class="space-y-4" @submit.prevent>
			<FormControl
				v-model="draft.title"
				label="Tier name"
				required
				placeholder="Gold"
				autocomplete="off"
				:disabled="!canWrite"
			/>
			<PriceList v-model="draft.prices" :disabled="!canWrite" />
			<FormControl
				:model-value="draft.slots"
				type="number"
				label="Slots"
				:min="0"
				description="Leave at 0 for any number of sponsors."
				:disabled="!canWrite"
				@update:model-value="draft.slots = Math.max(Number($event) || 0, 0)"
			/>
			<PerkList v-model="draft.perks" :disabled="!canWrite" />
		</form>

		<section class="space-y-2">
			<div class="flex items-center gap-3">
				<h3 class="text-xs uppercase tracking-wide text-ink-gray-5">Sponsors</h3>
				<span class="h-px flex-1 bg-outline-gray-1" aria-hidden="true" />
				<span class="text-xs tabular-nums text-ink-gray-5">{{ sponsorsInTier.length }}</span>
			</div>
			<div v-if="sponsorsInTier.length" class="grid grid-cols-2 gap-3">
				<SponsorCard
					v-for="sponsor in sponsorsInTier"
					:key="sponsor.name"
					:sponsor="sponsor"
					@open="emit('openSponsor', sponsor.name)"
				/>
			</div>
			<p v-else class="text-base text-ink-gray-5">No sponsors in this tier yet.</p>
		</section>

		<template v-if="canWrite && hasChanges" #footer>
			<DrawerSaveBar :disabled="isInvalid" @discard="discardChanges" @save="confirmAndSave" />
		</template>
	</SponsorshipDrawer>
</template>
