<script setup lang="ts">
import { Alert, FormControl, toast, useDoc } from "frappe-ui"
import { computed } from "vue"

import DrawerSaveBar from "@/components/dashboard/sponsorships/DrawerSaveBar.vue"
import { keepLastValue } from "@/components/dashboard/sponsorships/helpers"
import PerkList from "@/components/dashboard/sponsorships/PerkList.vue"
import PriceInput from "@/components/dashboard/sponsorships/PriceInput.vue"
import SponsorCard from "@/components/dashboard/sponsorships/SponsorCard.vue"
import SponsorshipDrawer from "@/components/dashboard/sponsorships/SponsorshipDrawer.vue"
import { useDrawerEdits } from "@/composables/useDrawerEdits"
import { useEnabledCurrencies } from "@/data/currencies"
import type { EventSponsorItem, SponsorshipTierItem } from "@/types"
import { formatWholePriceOrFree } from "@/utils/currency"

type TierValues = {
	title: string
	price: number
	currency: string
	perks: string[]
}
type TierDoc = Pick<TierValues, "title" | "price" | "currency"> & {
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

const isInvalid = computed(() => !draft.value.title?.trim() || !(draft.value.price >= 0))

const sponsorsInTier = computed(() => props.sponsors.filter((row) => row.tier === props.tier?.name))

const formattedPrice = computed(() =>
	props.tier ? formatWholePriceOrFree(props.tier.price, props.tier.currency || "INR") : "",
)

const enabledCurrencies = useEnabledCurrencies()

// A tier keeps its currency even if the site later disables it.
const currencyOptions = computed(() => {
	const currencyNames = (enabledCurrencies.data ?? []).map((currency) => currency.name)
	const tierCurrency = props.tier?.currency
	if (tierCurrency && !currencyNames.includes(tierCurrency)) currencyNames.unshift(tierCurrency)
	return currencyNames
})

const selectedCurrency = computed(() =>
	enabledCurrencies.data?.find((currency) => currency.name === draft.value.currency),
)

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
		price: tier.price,
		currency: tier.currency || "INR",
		perks: (tier.perks ?? "").split("\n").filter((perk) => perk.trim()),
	}
}

async function save(values: TierValues) {
	await tierDoc.setValue.submit({
		title: values.title.trim(),
		price: values.price,
		currency: values.currency,
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
		:show-avatar="false"
		:title="shownTier.title"
		:description="formattedPrice"
		:details="[]"
		title-in-header
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
			<div class="grid grid-cols-[2fr_1fr] gap-4">
				<PriceInput
					v-model="draft.price"
					label="Price"
					required
					:currency-symbol="selectedCurrency?.symbol || draft.currency"
					:number-format="selectedCurrency?.number_format"
					:disabled="!canWrite"
				/>
				<FormControl
					v-model="draft.currency"
					type="select"
					label="Currency"
					:options="currencyOptions"
					:disabled="!canWrite"
				/>
			</div>
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
