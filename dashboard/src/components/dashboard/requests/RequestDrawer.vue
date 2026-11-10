<script setup lang="ts">
import { Avatar, Badge, Button, Tooltip, dayjs, dayjsLocal } from "frappe-ui"
import { computed } from "vue"

import DetailRow from "@/components/common/DetailRow.vue"
import {
	Drawer,
	DrawerCloseButton,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import type { RegistrationRequest } from "@/types"
import { formatPriceOrFree } from "@/utils/currency"
import { isPaid, requesterName, ticketTypeOf } from "@/utils/requestQueue"
import {
	type RequestAction,
	REQUEST_VIEWS,
	type RequestView,
	requestButtons,
} from "@/utils/requestStatus"

import RequestActivity from "./RequestActivity.vue"
import RequestPosition from "./RequestPosition.vue"

const props = defineProps<{
	request: RegistrationRequest | null
	view: RequestView | null
	offerHours: number
	seatsFree: number
	hasPrevious: boolean
	hasNext: boolean
}>()
const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ previous: []; next: []; act: [action: RequestAction] }>()

const waitlist = computed(() => props.request?.request_type === "Waitlist")
const name = computed(() => (props.request ? requesterName(props.request) : ""))
const ticketType = computed(() => (props.request ? ticketTypeOf(props.request) : ""))
const status = computed(() => (props.view ? REQUEST_VIEWS[props.view] : null))
const paid = computed(() => Boolean(props.request && isPaid(props.request)))
const price = computed(() =>
	props.request
		? formatPriceOrFree(props.request.total_amount, props.request.currency ?? "INR")
		: "",
)
const requestedAt = computed(() => (props.request ? dayjsLocal(props.request.requested_at) : null))

const payment = computed(() => {
	const row = props.request
	if (row?.status !== "Payment Pending") return null
	if (!row.offer_expires_at) return "Link expired"
	const hours = Math.max(
		1,
		Math.ceil(dayjsLocal(row.offer_expires_at).diff(dayjs(), "minute") / 60),
	)
	return `Link sent · expires in ${hours}h`
})

// Secondary first, so the primary action sits at the reading end of the row.
const buttons = computed(() =>
	props.view ? requestButtons(props.view, paid.value).toReversed() : [],
)

const note = computed(() => {
	if (props.view !== "pending" && props.view !== "waiting") return null
	const verb = waitlist.value ? "Letting in" : "Approving"
	return paid.value
		? `${verb} sends a ${price.value} payment link · expires in ${props.offerHours}h`
		: `${verb} emails their ticket right away`
})
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="md">
			<template v-if="request && status">
				<div class="flex items-center gap-1 p-4 pb-0">
					<DrawerCloseButton label="Close request" />
					<span class="text-sm text-ink-gray-5">
						{{ waitlist ? `Waitlist · ${ticketType}` : "Approval request" }}
					</span>
					<div class="ml-auto flex items-center gap-1">
						<Tooltip text="Previous request">
							<Button
								variant="ghost"
								size="sm"
								icon="lucide-chevron-up"
								aria-label="Previous request"
								:disabled="!hasPrevious"
								@click="emit('previous')"
							/>
						</Tooltip>
						<Tooltip text="Next request">
							<Button
								variant="ghost"
								size="sm"
								icon="lucide-chevron-down"
								aria-label="Next request"
								:disabled="!hasNext"
								@click="emit('next')"
							/>
						</Tooltip>
					</div>
				</div>

				<div class="flex flex-1 flex-col gap-6 overflow-y-auto overscroll-contain p-4">
					<RequestPosition
						v-if="waitlist"
						:request="request"
						:status-label="status.label"
						:waiting="view === 'waiting'"
						:ticket-type="ticketType"
						:seats-free="seatsFree"
					/>

					<div class="flex items-center gap-3">
						<Avatar :label="name" size="2xl" />
						<div class="min-w-0 flex-1 space-y-1">
							<DrawerTitle class="truncate text-xl font-semibold text-ink-gray-9">
								{{ name }}
							</DrawerTitle>
							<DrawerDescription class="truncate text-base text-ink-gray-5">
								{{ request.buyer_email || "No email on this request" }}
							</DrawerDescription>
						</div>
						<Badge variant="subtle" size="md" :theme="status.theme" :label="status.label" />
					</div>

					<dl class="space-y-3 text-base">
						<DetailRow label="Ticket type">
							<Badge v-if="ticketType" variant="subtle" :label="ticketType" />
						</DetailRow>
						<DetailRow label="Price" :value="price" />
						<DetailRow :label="waitlist ? 'Joined' : 'Submitted'">
							<Tooltip v-if="requestedAt" :text="requestedAt.format('D MMM YYYY, h:mm A')">
								<span>{{ requestedAt.fromNow() }}</span>
							</Tooltip>
						</DetailRow>
						<DetailRow v-if="payment" label="Payment" :value="payment" />
						<DetailRow v-if="request.attendees.length > 1" label="Attendees">
							<ul class="space-y-1 whitespace-normal">
								<li v-for="(attendee, index) in request.attendees" :key="index">
									{{ attendee.full_name }}
									<span class="text-ink-gray-5">{{ attendee.email }}</span>
								</li>
							</ul>
						</DetailRow>
					</dl>

					<section v-if="request.answers.length" class="space-y-3">
						<h3 class="text-base font-semibold text-ink-gray-9">Registration answers</h3>
						<div v-for="(answer, index) in request.answers" :key="index" class="space-y-0.5">
							<p class="text-sm text-ink-gray-5">{{ answer.label }}</p>
							<p class="text-base text-pretty text-ink-gray-8">{{ answer.value || "—" }}</p>
						</div>
					</section>

					<RequestActivity :key="request.name" :request="request" />
				</div>

				<div v-if="buttons.length" class="shrink-0 space-y-2.5 border-t border-outline-gray-1 p-4">
					<p v-if="note" class="flex items-center gap-1.5 text-sm text-ink-gray-5">
						<span
							:class="paid ? 'lucide-credit-card' : 'lucide-mail'"
							class="size-3.5 shrink-0"
							aria-hidden="true"
						/>
						{{ note }}
					</p>
					<div class="flex gap-2">
						<Button
							v-for="(button, index) in buttons"
							:key="button.action"
							class="flex-1"
							size="md"
							:variant="index === buttons.length - 1 ? 'solid' : 'subtle'"
							:label="button.label"
							@click="emit('act', button.action)"
						/>
					</div>
				</div>
			</template>
		</DrawerContent>
	</Drawer>
</template>
