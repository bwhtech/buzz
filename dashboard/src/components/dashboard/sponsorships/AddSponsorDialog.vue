<script setup lang="ts">
import { Button, Dialog, ErrorMessage, FormControl, Spinner, toast, useNewDoc } from "frappe-ui"
import { computed, ref, watch } from "vue"

import ImageCropUploader from "@/components/common/ImageCropUploader.vue"
import LogoPanel from "@/components/dashboard/sponsorships/LogoPanel.vue"
import type { FrappeError, SponsorshipTierItem } from "@/types"
import { validateIsImageFile } from "@/utils"

type SponsorDoc = {
	event: string
	company_name: string
	company_logo: string
	website: string
	tier: string
}

const props = defineProps<{ event: string; tiers: SponsorshipTierItem[] }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ added: [] }>()

const companyName = ref("")
const logo = ref<string | null>(null)
const website = ref("")
const tier = ref("")
const showErrors = ref(false)

const creator = useNewDoc<SponsorDoc>("Event Sponsor")

const tierOptions = computed(() =>
	props.tiers.filter((row) => row.enabled).map((row) => ({ label: row.title, value: row.name })),
)
const invalid = computed(() => !companyName.value.trim() || !logo.value || !tier.value)
const errorMessage = computed(() => (creator.error as FrappeError | null)?.messages?.join("\n"))

watch(isOpen, (open) => open && reset())

function reset() {
	companyName.value = ""
	logo.value = null
	website.value = ""
	tier.value = tierOptions.value[0]?.value ?? ""
	showErrors.value = false
	creator.reset()
}

async function submit() {
	showErrors.value = true
	if (invalid.value) return

	Object.assign(creator.doc, {
		event: props.event,
		company_name: companyName.value.trim(),
		company_logo: logo.value,
		website: website.value.trim(),
		tier: tier.value,
	})
	await creator.submit().catch(() => null)
	if (creator.error) return

	toast.success(`${companyName.value.trim()} added as a sponsor`)
	emit("added")
	isOpen.value = false
}
</script>

<template>
	<Dialog v-model="isOpen" title="Add sponsor">
		<form novalidate class="space-y-4" @submit.prevent="submit">
			<ImageCropUploader
				:aspect-ratio="1"
				:output-width="512"
				:validate-file="validateIsImageFile"
				@success="(file: { file_url: string }) => (logo = file.file_url)"
			>
				<template #default="{ openFileSelector, error: uploadError, uploading }">
					<div class="space-y-2">
						<button
							type="button"
							class="relative block w-full rounded-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
							:aria-label="logo ? 'Change sponsor logo' : 'Upload sponsor logo'"
							@click="openFileSelector"
						>
							<LogoPanel
								size="lg"
								:src="logo"
								:name="companyName || 'Sponsor'"
								placeholder="Upload sponsor logo"
							/>
							<span
								v-if="uploading"
								class="absolute inset-0 flex items-center justify-center rounded-4 bg-surface-gray-2"
							>
								<Spinner class="size-5 text-ink-gray-5" />
							</span>
						</button>
						<div v-if="logo" class="flex gap-2">
							<Button size="sm" label="Change" @click="openFileSelector" />
							<Button size="sm" variant="ghost" label="Remove" @click="logo = null" />
						</div>
						<ErrorMessage :message="(uploadError as string) ?? ''" />
					</div>
				</template>
			</ImageCropUploader>
			<FormControl v-model="companyName" label="Company name" autocomplete="off" />
			<FormControl v-model="website" label="Website" placeholder="example.com" />
			<FormControl v-model="tier" type="select" label="Tier" :options="tierOptions" />

			<p v-if="showErrors && invalid" class="text-sm text-ink-red-4">
				A sponsor needs a name, a logo and a tier.
			</p>
			<ErrorMessage v-else-if="errorMessage" :message="errorMessage" />

			<Button
				type="button"
				variant="solid"
				class="w-full"
				label="Add sponsor"
				:loading="creator.loading"
				@click="submit"
			/>
		</form>
	</Dialog>
</template>
