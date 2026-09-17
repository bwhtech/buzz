<script setup lang="ts">
import { Button, Combobox, ErrorMessage, FormControl, useDoc } from "frappe-ui"
import { computed } from "vue"

import ImageCropUploader from "@/components/common/ImageCropUploader.vue"
import DrawerSaveBar from "@/components/dashboard/sponsorships/DrawerSaveBar.vue"
import { stripUrlScheme, websiteUrl } from "@/components/dashboard/sponsorships/helpers"
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
		v-if="sponsor"
		v-model:open="open"
		:title="sponsor.company_name"
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
