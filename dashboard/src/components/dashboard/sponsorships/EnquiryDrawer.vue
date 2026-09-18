<script setup lang="ts">
import {
	Button,
	Dialog,
	ErrorMessage,
	Select,
	Skeleton,
	Tooltip,
	dayjsLocal,
	toast,
} from "frappe-ui"
import {
	AccordionContent,
	AccordionHeader,
	AccordionItem,
	AccordionRoot,
	AccordionTrigger,
} from "reka-ui"
import { computed, ref, watch } from "vue"

import DetailRow from "@/components/common/DetailRow.vue"
import {
	Drawer,
	DrawerClose,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import {
	ENQUIRY_STATUSES,
	enquiryStatusDot,
	websiteUrl,
} from "@/components/dashboard/sponsorships/helpers"
import LogoPanel from "@/components/dashboard/sponsorships/LogoPanel.vue"
import { useCopyToClipboard } from "@/composables/useCopyToClipboard"
import { useEnquiryDetail, useUpdateEnquiryStatus } from "@/data/sponsorships"
import type { FrappeError } from "@/types"

const props = defineProps<{ enquiry: string | null; canWrite?: boolean }>()
const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ changed: [status: string]; openSponsor: [name: string] }>()

const detail = useEnquiryDetail(() => props.enquiry)
const update = useUpdateEnquiryStatus()
const copyToClipboard = useCopyToClipboard()

watch(
	() => props.enquiry,
	(name) => name && detail.fetch(),
	{ immediate: true },
)

const loaded = computed(() => (detail.data?.name === props.enquiry ? detail.data : null))
const errorMessage = computed(() => (detail.error as FrappeError | null)?.messages?.join("\n"))

// Seeded from what is stored, so a failed write leaves the control telling the truth.
const status = ref("")
watch(
	() => loaded.value?.status,
	(current) => (status.value = current || ""),
	{ immediate: true },
)
const statusOptions = ENQUIRY_STATUSES.map((value) => ({ value, label: value }))
const changed = computed(() => Boolean(status.value) && status.value !== loaded.value?.status)
// Settled outcomes are not walked back from here.
const LOCKED_STATUSES = ["Paid", "Cancelled", "Withdrawn"]
const locked = computed(() => LOCKED_STATUSES.includes(loaded.value?.status || ""))

// A disabled control should say why, not just refuse the click.
const statusHint = computed(() => {
	if (!props.canWrite) return "Only the event team can change this."
	if (locked.value)
		return `Status cannot be changed for ${loaded.value?.status.toLowerCase()} enquiries.`
	return ""
})

// These two reach outside the enquiry — an email to the applicant, a sponsor on the event.
const CONFIRMATIONS: Record<string, { title: string; message: string; action: string }> = {
	"Payment Pending": {
		title: "Approve this enquiry?",
		message: "The applicant is emailed that their sponsorship is approved and payment is due.",
		action: "Approve",
	},
	Paid: {
		title: "Mark as paid?",
		message: "This lists the company as a sponsor of the event without taking a payment.",
		action: "Mark as paid",
	},
}
const confirmation = computed(() => CONFIRMATIONS[status.value])
const confirming = ref(false)

function requestUpdate() {
	if (!changed.value) return
	if (confirmation.value) confirming.value = true
	else save()
}

async function save() {
	if (!props.enquiry) return
	const next = status.value
	await update.submit({ enquiry: props.enquiry, status: next })
	confirming.value = false
	if (update.error) {
		status.value = loaded.value?.status || ""
		const reason = (update.error as FrappeError | null)?.messages?.[0]
		toast.error(reason || "Could not change the status")
		return
	}
	toast.success(`Marked ${next.toLowerCase()}`)
	emit("changed", next)
	detail.fetch()
}

const details = computed(() => {
	const enquiry = loaded.value
	if (!enquiry) return []
	return [
		{ label: "Tier", value: enquiry.tier_title || "—" },
		{ label: "Submitted on", value: dayjsLocal(enquiry.creation).format("D MMM YYYY, h:mm A") },
		{
			label: "Contact",
			value: enquiry.contact || "—",
			link: enquiry.contact?.includes("@") ? `mailto:${enquiry.contact}` : null,
			copy: enquiry.contact,
		},
		{ label: "Phone", value: enquiry.phone || "—", link: enquiry.phone && `tel:${enquiry.phone}` },
		{
			label: "Website",
			value: enquiry.website || "—",
			link: websiteUrl(enquiry.website),
			copy: enquiry.website,
		},
		{ label: "Country", value: enquiry.country || "—" },
	]
})

const updatedAt = computed(() => (loaded.value ? dayjsLocal(loaded.value.modified) : null))
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent>
			<template v-if="enquiry">
				<div class="flex items-center gap-2 p-4 pb-0">
					<DrawerClose as-child>
						<Button size="sm" icon="lucide-chevrons-right" aria-label="Close enquiry" />
					</DrawerClose>
					<button
						type="button"
						class="cursor-copy font-mono text-sm tracking-wider uppercase text-ink-gray-5 hover:text-ink-gray-7"
						:aria-label="`Copy enquiry id ${enquiry}`"
						@click="copyToClipboard(enquiry, 'Enquiry ID copied')"
					>
						#{{ enquiry }}
					</button>
				</div>

				<div class="flex flex-1 flex-col space-y-4 overflow-y-auto p-4">
					<div v-if="!loaded && detail.loading" class="space-y-4">
						<Skeleton class="h-7 w-40 rounded-4" />
						<Skeleton class="h-40 w-full rounded-6" />
						<Skeleton class="h-9 w-2/3 rounded-4" />
					</div>
					<ErrorMessage v-else-if="errorMessage" :message="errorMessage" />

					<template v-if="loaded">
						<Tooltip :text="statusHint" :disabled="!statusHint">
							<Select
								v-model="status"
								class="w-fit"
								size="md"
								aria-label="Enquiry status"
								side="bottom"
								:options="statusOptions"
								:disabled="!canWrite || locked || update.loading"
							>
								<template #item-prefix="{ item }">
									<span
										class="size-2 shrink-0 rounded-full transition-colors duration-150"
										:class="enquiryStatusDot(String(item.value))"
										aria-hidden="true"
									/>
								</template>
							</Select>
						</Tooltip>

						<LogoPanel size="lg" :src="loaded.company_logo" :name="loaded.company_name" />

						<DrawerTitle class="text-4xl font-semibold text-pretty text-ink-gray-9">
							{{ loaded.company_name }}
						</DrawerTitle>
						<DrawerDescription class="sr-only">
							Sponsorship enquiry, {{ loaded.status }}
						</DrawerDescription>

						<dl class="space-y-3 text-base">
							<DetailRow v-for="field in details" :key="field.label" :label="field.label">
								<a
									v-if="field.link"
									:href="field.link"
									target="_blank"
									rel="noopener"
									class="block truncate underline decoration-outline-gray-3 underline-offset-2 hover:text-ink-gray-9"
								>
									{{ field.value }}
								</a>
								<span v-else>{{ field.value }}</span>

								<template v-if="field.copy" #suffix>
									<Button
										variant="ghost"
										size="sm"
										icon="lucide-copy"
										:aria-label="`Copy ${field.label.toLowerCase()}`"
										@click="copyToClipboard(field.copy, `${field.label} copied`)"
									/>
								</template>
							</DetailRow>
						</dl>

						<div v-if="loaded.answers.length" class="space-y-2 pt-4">
							<h3 class="text-lg font-semibold text-ink-gray-9">Form answers</h3>
							<AccordionRoot
								:key="loaded.name"
								type="multiple"
								:default-value="loaded.answers.map((_, index) => String(index))"
								class="divide-y divide-outline-gray-1"
							>
								<AccordionItem
									v-for="(answer, index) in loaded.answers"
									:key="`${index}-${answer.label}`"
									:value="String(index)"
								>
									<AccordionHeader>
										<AccordionTrigger
											class="group flex w-full items-center justify-between gap-2 py-2.5 text-left text-base text-ink-gray-8 focus-visible:outline-none focus-visible:focus-ring"
										>
											{{ answer.label }}
											<span
												class="lucide-chevron-down size-4 shrink-0 text-ink-gray-5 transition-transform duration-150 group-data-[state=open]:rotate-180"
												aria-hidden="true"
											/>
										</AccordionTrigger>
									</AccordionHeader>
									<AccordionContent class="answer text-base text-ink-gray-6">
										<div class="whitespace-pre-line break-words pb-3">
											{{ answer.value || "No answer" }}
										</div>
									</AccordionContent>
								</AccordionItem>
							</AccordionRoot>
						</div>
					</template>
				</div>

				<Dialog
					v-if="confirmation"
					v-model:open="confirming"
					:title="confirmation.title"
					:message="confirmation.message"
					size="md"
				>
					<template #actions>
						<div class="flex justify-end gap-2">
							<Button label="Not yet" @click="confirming = false" />
							<Button
								variant="solid"
								:label="confirmation.action"
								:loading="update.loading"
								@click="save"
							/>
						</div>
					</template>
				</Dialog>
			</template>

			<template v-if="loaded" #footer>
				<Tooltip v-if="updatedAt" :text="updatedAt.format('D MMM YYYY, h:mm A')">
					<p class="flex items-center gap-1 text-xs text-ink-gray-5">
						<span class="lucide-clock-fading size-3.5 shrink-0" aria-hidden="true" />
						Updated {{ updatedAt.fromNow() }}
					</p>
				</Tooltip>

				<div v-if="canWrite && changed" class="flex items-center gap-2">
					<Button
						variant="solid"
						size="sm"
						label="Update"
						:loading="update.loading"
						@click="requestUpdate"
					/>
					<Button size="sm" label="Cancel" @click="status = loaded.status" />
				</div>

				<Button
					v-if="loaded.sponsor"
					class="ml-auto"
					variant="outline"
					size="sm"
					label="View sponsor"
					@click="emit('openSponsor', loaded.sponsor)"
				/>
			</template>
		</DrawerContent>
	</Drawer>
</template>

<style scoped>
/* reka measures the panel and exposes its height; without it the answers snap open. */
.answer {
	overflow: hidden;
}

.answer[data-state="open"] {
	animation: answer-open 200ms cubic-bezier(0.23, 1, 0.32, 1);
}

.answer[data-state="closed"] {
	animation: answer-close 150ms cubic-bezier(0.23, 1, 0.32, 1);
}

@keyframes answer-open {
	from {
		height: 0;
	}
	to {
		height: var(--reka-accordion-content-height);
	}
}

@keyframes answer-close {
	from {
		height: var(--reka-accordion-content-height);
	}
	to {
		height: 0;
	}
}

@media (prefers-reduced-motion: reduce) {
	.answer[data-state="open"],
	.answer[data-state="closed"] {
		animation: none;
	}
}
</style>
