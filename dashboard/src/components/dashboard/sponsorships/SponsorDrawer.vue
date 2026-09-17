<script setup lang="ts">
import { Button, Combobox, ErrorMessage, FormControl, dialog, toast, useDoc } from "frappe-ui"
import { computed } from "vue"

import ImageCropUploader from "@/components/common/ImageCropUploader.vue"
import DrawerSaveBar from "@/components/dashboard/sponsorships/DrawerSaveBar.vue"
import {
	keepLastValue,
	stripUrlScheme,
	websiteUrl,
} from "@/components/dashboard/sponsorships/helpers"
import LogoPanel from "@/components/dashboard/sponsorships/LogoPanel.vue"
import SponsorshipDrawer from "@/components/dashboard/sponsorships/SponsorshipDrawer.vue"
import WebsiteInput from "@/components/dashboard/sponsorships/WebsiteInput.vue"
import { useDrawerEdits } from "@/composables/useDrawerEdits"
import { useCountries } from "@/data/countries"
import type { EventSponsorItem, SponsorshipTierItem } from "@/types"
import { validateIsImageFile } from "@/utils"

type SponsorValues = {
	company_name: string
	company_logo: string
	website: string
	country: string | null
	tier: string
	contact_email: string
}

const props = defineProps<{
	sponsor: EventSponsorItem | null
	tiers: SponsorshipTierItem[]
	canWrite: boolean
}>()
const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ changed: []; openEnquiry: [name: string] }>()

const shownSponsor = keepLastValue(() => props.sponsor)

const sponsorDoc = useDoc<SponsorValues & { name: string }>({
	doctype: "Event Sponsor",
	name: () => props.sponsor?.name ?? "",
	immediate: false,
})

const { draft, hasChanges, discardChanges, confirmAndSave } = useDrawerEdits<SponsorValues>(
	() => props.sponsor?.name,
	() => props.sponsor && toSponsorValues(props.sponsor),
	save,
	{
		title: "Save sponsor",
		message: "The event site will show the updated sponsor details.",
		success: "Sponsor updated",
	},
)

const isInvalid = computed(
	() => !draft.value.company_name?.trim() || !draft.value.tier || !draft.value.company_logo,
)

const countries = useCountries()
const countryOptions = computed(() =>
	(countries.data ?? []).map((country) => ({ label: country.name, value: country.name })),
)

// A sponsor keeps its tier even once that tier is disabled, so it stays selectable here.
const tierOptions = computed(() =>
	props.tiers
		.filter((tier) => tier.enabled || tier.name === props.sponsor?.tier)
		.map((tier) => ({ label: tier.title, value: tier.name })),
)

function toSponsorValues(sponsor: EventSponsorItem): SponsorValues {
	return {
		company_name: sponsor.company_name,
		company_logo: sponsor.company_logo || "",
		website: stripUrlScheme(sponsor.website || ""),
		country: sponsor.country,
		tier: sponsor.tier || "",
		contact_email: sponsor.contact_email || "",
	}
}

function confirmRemove() {
	const sponsor = shownSponsor.value
	if (!sponsor) return
	dialog.confirm({
		title: "Remove this sponsor?",
		message: `Sponsor ${sponsor.company_name} will be removed from the website.`,
		theme: "red",
		confirmLabel: "Remove",
		onConfirm: async () => {
			await sponsorDoc.delete.submit()
			// useCall settles either way, so the failure has to be rethrown to reach the dialog.
			if (sponsorDoc.delete.error) throw sponsorDoc.delete.error
			open.value = false
			toast.success(`${sponsor.company_name} is no longer a sponsor of this event.`)
			emit("changed")
		},
	})
}

async function save(values: SponsorValues) {
	await sponsorDoc.setValue.submit({
		...values,
		company_name: values.company_name.trim(),
		website: websiteUrl(values.website.trim()) || "",
	})
	if (sponsorDoc.setValue.error) throw sponsorDoc.setValue.error
	emit("changed")
}
</script>

<template>
	<SponsorshipDrawer
		v-if="shownSponsor"
		v-model:open="open"
		:title="shownSponsor.company_name"
		description="Confirmed sponsor"
		:show-avatar="false"
		:details="[]"
		title-in-header
	>
		<template #notice>
			<ImageCropUploader
				:aspect-ratio="1"
				:output-width="512"
				:validate-file="validateIsImageFile"
				@success="(file: { file_url: string }) => (draft.company_logo = file.file_url)"
			>
				<template #default="{ openFileSelector, error: uploadError, uploading }">
					<div class="space-y-2">
						<LogoPanel
							size="lg"
							:src="draft.company_logo"
							:name="draft.company_name"
							:editable="canWrite"
							:replacing="uploading"
							@replace="openFileSelector"
						/>
						<ErrorMessage :message="(uploadError as string) ?? ''" />
					</div>
				</template>
			</ImageCropUploader>
		</template>

		<form novalidate class="space-y-4" @submit.prevent>
			<FormControl
				v-model="draft.company_name"
				label="Company name"
				required
				autocomplete="off"
				:disabled="!canWrite"
			/>
			<WebsiteInput v-model="draft.website" :disabled="!canWrite" />
			<div class="grid grid-cols-2 gap-4">
				<Combobox
					v-model="draft.country"
					label="Country"
					placeholder="Select country"
					:options="countryOptions"
					:disabled="!canWrite"
				/>
				<FormControl
					v-model="draft.tier"
					type="select"
					label="Tier"
					required
					:options="tierOptions"
					:disabled="!canWrite"
				/>
			</div>
			<FormControl
				v-model="draft.contact_email"
				type="email"
				label="Contact email"
				placeholder="name@example.com"
				autocomplete="off"
				:disabled="!canWrite"
			/>
		</form>

		<Button
			v-if="shownSponsor.enquiry"
			class="w-fit"
			icon-right="lucide-arrow-right"
			label="View enquiry"
			@click="emit('openEnquiry', shownSponsor.enquiry)"
		/>

		<template v-if="canWrite" #footer>
			<DrawerSaveBar
				v-if="hasChanges"
				:disabled="isInvalid"
				@discard="discardChanges"
				@save="confirmAndSave"
			/>
			<Button
				class="ml-auto"
				variant="ghost"
				theme="red"
				label="Remove Sponsor"
				:loading="sponsorDoc.delete.loading"
				@click="confirmRemove"
			/>
		</template>
	</SponsorshipDrawer>
</template>
