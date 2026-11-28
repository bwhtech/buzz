<script setup lang="ts">
import { Alert, Button, ErrorMessage, dayjsLocal, toast, useDoc, useNewDoc } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { useRouter } from "vue-router"

import {
	Drawer,
	DrawerCloseButton,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import EnabledAlert from "@/components/dashboard/EnabledAlert.vue"
import { keepLastValue } from "@/components/dashboard/sponsorships/helpers"
import { useIsMobile } from "@/composables/useIsMobile"
import type { CouponItem, CouponTicketType } from "@/types"
import { CouponAvailability } from "@/utils/couponAvailability"
import {
	type CouponValues,
	blankCouponValues,
	couponDocValues,
	couponError,
	couponValuesOf,
} from "@/utils/couponForm"
import { matches } from "@/utils/formDraft"
import { serverErrorMessage } from "@/utils/serverError"

import AccessCodePreview from "./AccessCodePreview.vue"
import CouponCheckoutPreview from "./CouponCheckoutPreview.vue"
import CouponForm from "./CouponForm.vue"
import CouponTypeStep from "./CouponTypeStep.vue"

const props = defineProps<{
	event: string
	// null opens the drawer on a new coupon.
	coupon: CouponItem | null
	// The type a new coupon starts on.
	newCouponType?: CouponValues["coupon_type"]
	ticketTypes: CouponTicketType[]
	eventEndDate: string | null
	canWrite: boolean
}>()
const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ changed: [] }>()

const shownCoupon = keepLastValue(() => props.coupon)
const isMobile = useIsMobile()
const isNew = computed(() => !props.coupon)

const step = ref<1 | 2>(1)
const draft = ref<CouponValues>(blankCouponValues())
const savedValues = computed(() => (props.coupon ? couponValuesOf(props.coupon) : null))

const availability = computed(() => new CouponAvailability(props.ticketTypes))
const router = useRouter()

// The preview waits for a picked type, so step 1 has the whole width for the choice.
const showPreview = computed(() => !isMobile.value && step.value === 2)
const freeEventAlert = computed(() => {
	const description = availability.value.freeEventMessage
	if (step.value !== 1 || !description) return null
	const nothingAllowed = !availability.value.firstAllowedType
	return {
		theme: nothingAllowed ? ("amber" as const) : ("blue" as const),
		title: nothingAllowed ? "Nothing to create yet" : "This event is free",
		description,
		primaryAction: {
			label: "Add a paid ticket type",
			variant: "outline" as const,
			theme: "gray" as const,
			onClick: () => {
				router.push({ name: "event-registrations", params: { eventId: props.event } })
			},
		},
	}
})
const canContinue = computed(() => availability.value.allowsType(draft.value.coupon_type))

// A new coupon starts on a type the event allows, so Continue never leads to a form
// that can't save.
function startingType() {
	const wanted = props.newCouponType ?? "Promo Code"
	if (availability.value.allowsType(wanted)) return wanted
	return availability.value.firstAllowedType ?? wanted
}

// A fresh copy each time: sharing savedValues' object would let edits change it too.
const resetDraft = () =>
	(draft.value = props.coupon ? couponValuesOf(props.coupon) : blankCouponValues(startingType()))

watch(open, (opened) => {
	if (!opened) return
	resetDraft()
	showValidationError.value = false
	step.value = isNew.value ? 1 : 2
})

const hasChanges = computed(() => !!savedValues.value && !matches(draft.value, savedValues.value))
const validationError = computed(() => couponError(draft.value, props.ticketTypes))
// Shown only after a save attempt, then live until the drawer reopens.
const showValidationError = ref(false)

const creator = useNewDoc<Record<string, unknown>>("Buzz Coupon Code")
const couponDoc = useDoc<Record<string, unknown> & { name: string }>({
	doctype: "Buzz Coupon Code",
	name: () => props.coupon?.name ?? "",
	immediate: false,
})

const title = computed(() => {
	if (isNew.value) return "New coupon"
	return shownCoupon.value?.code ?? ""
})

const TYPE_TITLES = {
	"Promo Code": "Promo code",
	Automatic: "Automatic",
	"Access Code": "Access code",
}
const DISCOUNT_TITLES = {
	Percentage: "Percentage off",
	"Flat Amount": "Fixed amount off",
	None: "No discount",
}
const TYPE_ICONS = {
	"Promo Code": "lucide-ticket-percent",
	Automatic: "lucide-zap",
	"Access Code": "lucide-key-round",
}

const typeSummary = computed(() =>
	[TYPE_TITLES[draft.value.coupon_type], DISCOUNT_TITLES[draft.value.discount_type]].join(" · "),
)

// A coupon someone has used keeps its type, so past receipts still read true.
const canChangeType = computed(() => props.canWrite && !shownCoupon.value?.times_used)

const couponStatus = computed(() => {
	const coupon = shownCoupon.value
	if (!coupon) return undefined
	if (!coupon.enabled) return { theme: "gray" as const, title: "Coupon is disabled" }
	if (coupon.status === "Used up") return { theme: "amber" as const, title: "No uses left" }
	if (coupon.status === "Ended") return { theme: "gray" as const, title: "Coupon has ended" }
	if (coupon.status === "Scheduled")
		return {
			theme: "blue" as const,
			title: `Goes live on ${dayjsLocal(coupon.starts_on ?? undefined).format("D MMM YYYY")}`,
		}
	return { theme: "green" as const, title: "Coupon is active" }
})

async function create() {
	if (creator.loading) return
	Object.assign(creator.doc, {
		event: props.event,
		...couponDocValues(draft.value, props.ticketTypes),
	})
	await creator.submit().catch(() => null)
	if (creator.error) {
		toast.error(serverErrorMessage(creator.error))
		return
	}
	toast.success("Coupon created")
	emit("changed")
	open.value = false
}

function submit() {
	showValidationError.value = true
	if (validationError.value) return
	if (isNew.value) create()
	else saveChanges()
}

async function saveChanges() {
	await couponDoc.setValue.submit(couponDocValues(draft.value, props.ticketTypes)).catch(() => null)
	if (couponDoc.setValue.error) {
		toast.error(serverErrorMessage(couponDoc.setValue.error))
		return
	}
	toast.success("Coupon updated")
	emit("changed")
}

// Back a step first, then drop unsaved edits, then close.
function goBack() {
	if (step.value === 2 && isNew.value) step.value = 1
	else if (step.value === 1 && !isNew.value) step.value = 2
	else if (hasChanges.value) resetDraft()
	else open.value = false
}
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="2xl" :close-on-outside-click="!isNew">
			<div class="flex items-center gap-1 p-4 pb-2">
				<DrawerCloseButton />
				<DrawerTitle class="ml-1 truncate text-lg font-semibold text-ink-gray-9">{{
					title
				}}</DrawerTitle>
				<DrawerDescription class="sr-only">{{ typeSummary }}</DrawerDescription>
				<div
					v-if="isNew"
					class="ml-auto flex items-center gap-2 text-sm text-ink-gray-5"
					aria-live="polite"
				>
					<span class="flex gap-1" aria-hidden="true">
						<span class="h-[3px] w-4 rounded-full bg-surface-gray-8" />
						<span
							class="h-[3px] w-4 rounded-full transition-colors duration-200"
							:class="step === 2 ? 'bg-surface-gray-8' : 'bg-surface-gray-3'"
						/>
					</span>
					Step {{ step }} of 2
				</div>
			</div>

			<div class="flex min-h-0 flex-1">
				<!-- Slides in from the drawer's edge once a type is picked; leaves faster. -->
				<Transition
					enter-active-class="transition-[opacity,transform] duration-[240ms] ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-opacity"
					enter-from-class="opacity-0 -translate-x-4 motion-reduce:translate-x-0"
					leave-active-class="transition-opacity duration-100 ease-out"
					leave-to-class="opacity-0"
				>
					<aside
						v-if="showPreview"
						class="w-[360px] shrink-0 overflow-y-auto border-r border-outline-gray-1 bg-surface-gray-1 p-5"
					>
						<AccessCodePreview
							v-if="draft.coupon_type === 'Access Code'"
							:values="draft"
							:ticket-types="ticketTypes"
						/>
						<CouponCheckoutPreview v-else :values="draft" :ticket-types="ticketTypes" />
					</aside>
				</Transition>
				<div class="flex min-w-0 flex-1 flex-col">
					<div class="flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto overscroll-contain p-4">
						<EnabledAlert
							v-if="!isNew && shownCoupon"
							noun="Coupon"
							:enabled="!!shownCoupon.enabled"
							:editable="canWrite"
							field="enabled"
							:status="couponStatus"
							:set-value="couponDoc.setValue"
							@changed="emit('changed')"
						/>

						<!-- A short crossfade so the step swap doesn't jump; the exit is quicker than the entry. -->
						<Transition
							mode="out-in"
							enter-active-class="transition-[opacity,transform] duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-opacity"
							enter-from-class="opacity-0 translate-y-1 motion-reduce:translate-y-0"
							leave-active-class="transition-opacity duration-100 ease-out"
							leave-to-class="opacity-0"
						>
							<div v-if="step === 1" class="flex flex-col gap-6">
								<Alert v-if="freeEventAlert" v-bind="freeEventAlert" />
								<CouponTypeStep
									v-model:coupon-type="draft.coupon_type"
									v-model:discount-type="draft.discount_type"
									:availability="availability"
									:columns="3"
								/>
							</div>

							<div v-else class="flex flex-col gap-6">
								<div class="flex items-center gap-3 rounded-4 bg-surface-gray-1 py-2 pl-3 pr-1.5">
									<span
										class="size-4 shrink-0 text-ink-gray-6"
										:class="TYPE_ICONS[draft.coupon_type]"
										aria-hidden="true"
									/>
									<span class="flex-1 text-sm text-ink-gray-8">{{ typeSummary }}</span>
									<Button v-if="canChangeType" variant="ghost" label="Change" @click="step = 1" />
								</div>
								<CouponForm
									v-model="draft"
									:ticket-types="ticketTypes"
									:event-end-date="eventEndDate"
									:disabled="!canWrite"
								/>
							</div>
						</Transition>
					</div>

					<CouponCheckoutPreview
						v-if="isMobile && step === 2 && draft.coupon_type !== 'Access Code'"
						:values="draft"
						:ticket-types="ticketTypes"
						compact
					/>

					<!-- Sits under the form only, so the preview panel runs the full height. Slides up
					     when an edit makes it appear; leaves faster than it arrives. -->
					<Transition
						enter-active-class="transition-[opacity,transform] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-opacity"
						enter-from-class="opacity-0 translate-y-2 motion-reduce:translate-y-0"
						leave-active-class="transition-opacity duration-150 ease-out"
						leave-to-class="opacity-0"
					>
						<div
							v-if="canWrite && (isNew || hasChanges || step === 1)"
							class="shrink-0 border-t border-outline-gray-1 p-4"
						>
							<div class="flex w-full flex-wrap items-center justify-end gap-x-4 gap-y-2">
								<ErrorMessage
									v-if="showValidationError && step === 2"
									class="text-right"
									:message="validationError ?? undefined"
								/>
								<div class="flex justify-end gap-2 max-sm:w-full max-sm:[&>*]:flex-1">
									<Button
										size="md"
										:label="isNew && step === 2 ? 'Back' : 'Cancel'"
										@click="goBack"
									/>
									<Button
										v-if="step === 1"
										size="md"
										variant="solid"
										label="Continue"
										:disabled="!canContinue"
										@click="step = 2"
									/>
									<Button
										v-else
										size="md"
										variant="solid"
										:label="isNew ? 'Create coupon' : 'Save changes'"
										:loading="isNew ? creator.loading : couponDoc.setValue.loading"
										@click="submit"
									/>
								</div>
							</div>
						</div>
					</Transition>
				</div>
			</div>
		</DrawerContent>
	</Drawer>
</template>
