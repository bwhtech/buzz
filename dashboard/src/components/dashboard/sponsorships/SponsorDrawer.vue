<script setup lang="ts">
import { Button, FormControl, useDoc } from "frappe-ui"
import { computed } from "vue"

import DrawerSaveBar from "@/components/dashboard/sponsorships/DrawerSaveBar.vue"
import LogoPanel from "@/components/dashboard/sponsorships/LogoPanel.vue"
import SponsorshipDrawer, {
	type DrawerDetail,
} from "@/components/dashboard/sponsorships/SponsorshipDrawer.vue"
import { useDrawerEdits } from "@/composables/useDrawerEdits"
import type { EventSponsorItem, SponsorshipTierItem } from "@/types"

type SponsorValues = { company_name: string; website: string; tier: string }

const props = defineProps<{
	sponsor: EventSponsorItem | null
	tiers: SponsorshipTierItem[]
	canWrite: boolean
}>()
const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ changed: []; openEnquiry: [name: string] }>()

const sponsorDoc = useDoc<SponsorValues & { name: string }>({
	doctype: "Event Sponsor",
	name: () => props.sponsor?.name ?? "",
	immediate: false,
})

const { draft, hasChanges, discardChanges, confirmAndSave } = useDrawerEdits<SponsorValues>(
	() => props.sponsor?.name,
	() =>
		props.sponsor && {
			company_name: props.sponsor.company_name,
			website: props.sponsor.website || "",
			tier: props.sponsor.tier || "",
		},
	save,
	{
		title: "Save sponsor",
		message: "The event site will show the updated sponsor details.",
		success: "Sponsor updated",
	},
)

const isInvalid = computed(() => !draft.value.company_name?.trim() || !draft.value.tier)

// A sponsor keeps its tier even once that tier is disabled, so it stays selectable here.
const tierOptions = computed(() =>
	props.tiers
		.filter((tier) => tier.enabled || tier.name === props.sponsor?.tier)
		.map((tier) => ({ label: tier.title, value: tier.name })),
)

const details = computed<DrawerDetail[]>(() => [
	{ label: "Country", value: props.sponsor?.country },
])

async function save(values: SponsorValues) {
	await sponsorDoc.setValue.submit({ ...values, company_name: values.company_name.trim() })
	if (sponsorDoc.setValue.error) throw sponsorDoc.setValue.error
	emit("changed")
}
</script>

<template>
	<SponsorshipDrawer
		v-if="sponsor"
		v-model:open="open"
		:title="sponsor.company_name"
		description="Confirmed sponsor"
		:show-avatar="false"
		:details="details"
	>
		<template #notice>
			<LogoPanel size="lg" :src="sponsor.company_logo" :name="sponsor.company_name" />
		</template>

		<form novalidate class="space-y-4" @submit.prevent>
			<FormControl
				v-model="draft.company_name"
				label="Company name"
				autocomplete="off"
				:disabled="!canWrite"
			/>
			<FormControl
				v-model="draft.website"
				label="Website"
				placeholder="example.com"
				:disabled="!canWrite"
			/>
			<FormControl
				v-model="draft.tier"
				type="select"
				label="Tier"
				:options="tierOptions"
				:disabled="!canWrite"
			/>
		</form>

		<Button
			v-if="sponsor.enquiry"
			class="w-fit"
			icon-left="lucide-inbox"
			label="View enquiry"
			@click="emit('openEnquiry', sponsor.enquiry)"
		/>

		<template v-if="canWrite && hasChanges" #footer>
			<DrawerSaveBar :disabled="isInvalid" @discard="discardChanges" @save="confirmAndSave" />
		</template>
	</SponsorshipDrawer>
</template>
