<script setup lang="ts">
import { Alert, Button, ErrorMessage, dayjs, dayjsLocal, dialog, toast } from "frappe-ui"
import { computed, ref } from "vue"

import {
	Drawer,
	DrawerCloseButton,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import ImageCropUploader from "@/components/common/ImageCropUploader.vue"
import EventHoverCard from "@/components/dashboard/events/EventHoverCard.vue"
import { enquiryPrice, enquiryStatusTheme } from "@/components/dashboard/sponsorships/helpers"
import LogoPanel from "@/components/dashboard/sponsorships/LogoPanel.vue"
import {
	enquiryActions,
	enquiryStatusMessage,
} from "@/components/dashboard/sponsorships/mine/enquiryStatus"
import SponsorshipPaymentDialog from "@/components/SponsorshipPaymentDialog.vue"
import { useCopyToClipboard } from "@/composables/useCopyToClipboard"
import { useUpdateSponsorshipLogo, useWithdrawEnquiry } from "@/data/sponsorships"
import type { SponsorshipListItem } from "@/types"
import { validateIsImageFile } from "@/utils"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ enquiry: SponsorshipListItem | null; paymentReceived?: boolean }>()

const open = defineModel<boolean>("open", { required: true })

const emit = defineEmits<{ changed: [] }>()

const actions = computed(() => enquiryActions(props.enquiry?.status || ""))

const withdrawal = useWithdrawEnquiry()
const logo = useUpdateSponsorshipLogo(() => props.enquiry)
const copyId = useCopyToClipboard()

const paying = ref(false)

function confirmWithdrawal() {
	dialog.confirm({
		title: "Withdraw this enquiry?",
		message: "The event team stops considering it, and you cannot put it back yourself.",
		theme: "red",
		confirmLabel: "Withdraw",
		onConfirm: async () => {
			try {
				await withdrawal.submit({ enquiry_id: props.enquiry?.name || "" })
			} catch (error) {
				toast.error(serverErrorMessage(error) || "Could not withdraw the enquiry")
				throw error
			}
			toast.success("Enquiry withdrawn")
			emit("changed")
		},
	})
}

async function replaceLogo(file: { file_url: string }) {
	try {
		await logo.submit({ company_logo: file.file_url })
		toast.success("Logo updated")
		emit("changed")
	} catch {
		toast.error("Could not update the logo")
	}
}

const price = computed(() => (props.enquiry ? enquiryPrice(props.enquiry) : ""))

// Plain dayjs: start_date is date-only, and a timezone shift moves it a day back.
const eventDate = computed(() =>
	props.enquiry?.start_date ? dayjs(props.enquiry.start_date).format("D MMMM YYYY") : "",
)

const fields = computed(() => {
	const enquiry = props.enquiry
	if (!enquiry) return []
	return [
		{ label: "Tier", value: enquiry.tier_title || "Not chosen yet" },
		{ label: "Price", value: price.value || "—" },
		{ label: "Submitted on", value: dayjsLocal(enquiry.creation).format("D MMM YYYY") },
		{ label: "Sponsorship", value: enquiry.has_sponsor ? "Confirmed" : "Not confirmed yet" },
	]
})
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="lg">
			<template v-if="enquiry">
				<div class="flex items-center gap-2 p-4 pb-0">
					<DrawerCloseButton />
					<button
						type="button"
						class="cursor-copy font-mono text-sm tracking-wider uppercase text-ink-gray-5"
						:aria-label="`Copy enquiry id ${enquiry.name}`"
						@click="copyId(enquiry.name)"
					>
						#{{ enquiry.name }}
					</button>
				</div>

				<div class="flex flex-1 flex-col space-y-4 overflow-y-auto overscroll-contain p-4">
					<Alert
						v-if="paymentReceived"
						theme="green"
						title="Payment successful"
						description="Your sponsorship payment is confirmed. The details are on their way to your email."
					/>
					<!-- The status leads: it is the answer the applicant opened the drawer for. -->
					<Alert
						v-else
						:theme="enquiryStatusTheme(enquiry.status)"
						:title="enquiry.status"
						:description="enquiryStatusMessage(enquiry.status)"
					/>

					<div class="space-y-2">
						<DrawerTitle class="text-4xl font-semibold text-pretty text-ink-gray-9">
							{{ enquiry.company_name }}
						</DrawerTitle>
						<DrawerDescription class="text-base text-ink-gray-6">
							<EventHoverCard
								class="text-ink-gray-6"
								:title="enquiry.event_title || 'Deleted event'"
								:start-date="enquiry.start_date"
								:start-time="enquiry.start_time"
								:venue="enquiry.venue"
								:banner-image="enquiry.banner_image"
							/>
							<template v-if="eventDate"> · {{ eventDate }}</template>
						</DrawerDescription>
					</div>

					<ImageCropUploader
						:aspect-ratio="1"
						:output-width="512"
						:validate-file="validateIsImageFile"
						@success="replaceLogo"
					>
						<template #default="{ openFileSelector, error: uploadError, uploading }">
							<div class="space-y-2">
								<LogoPanel
									size="lg"
									:src="enquiry.company_logo"
									:name="enquiry.company_name"
									editable
									:replacing="uploading || logo.loading"
									@replace="openFileSelector"
								/>
								<ErrorMessage :message="(uploadError as string) ?? ''" />
							</div>
						</template>
					</ImageCropUploader>

					<div class="grid grid-cols-2 gap-x-5 gap-y-3">
						<div v-for="field in fields" :key="field.label" class="space-y-0.5">
							<p class="text-base text-ink-gray-5">{{ field.label }}</p>
							<p class="text-base font-medium text-ink-gray-8">{{ field.value }}</p>
						</div>
					</div>
				</div>

				<SponsorshipPaymentDialog
					v-if="actions.canPay"
					v-model:open="paying"
					:enquiry-id="enquiry.name"
					:event-id="enquiry.event"
					:event-title="enquiry.event_title || ''"
				/>
			</template>

			<template v-if="enquiry && (actions.canPay || actions.canWithdraw)" #footer>
				<Button
					v-if="actions.canPay"
					variant="solid"
					size="md"
					label="Pay now"
					@click="paying = true"
				/>
				<Button
					v-if="actions.canWithdraw"
					variant="ghost"
					theme="red"
					size="md"
					label="Withdraw"
					@click="confirmWithdrawal"
				/>
			</template>
		</DrawerContent>
	</Drawer>
</template>
