<script setup lang="ts">
import { Icon, TabButtons } from "frappe-ui"
import { computed, reactive, ref } from "vue"

import type { CouponTicketType } from "@/types"
import { type CouponValues, eligibleTicketTypes } from "@/utils/couponForm"
import { wholeAmount } from "@/utils/couponLabels"
import { checkoutPreview } from "@/utils/couponPreview"

const props = defineProps<{
	values: CouponValues
	ticketTypes: CouponTicketType[]
	// A one-line bar that expands, for the phone sheet.
	compact?: boolean
}>()

const pick = reactive<{ ticketType?: string; currency?: string }>({})
const expanded = ref(false)

const eligible = computed(() => eligibleTicketTypes(props.values, props.ticketTypes))
const preview = computed(() => checkoutPreview(props.values, props.ticketTypes, pick))
const ticketType = computed(() =>
	eligible.value.find((row) => row.name === preview.value?.ticketType),
)
const currencies = computed(() =>
	(ticketType.value?.prices ?? []).filter((row) => row.price > 0).map((row) => row.currency),
)

const isCode = computed(() => props.values.coupon_type === "Promo Code")
const money = (amount: number) => wholeAmount(amount, preview.value?.currency ?? "INR")
const line = computed(() => `${ticketType.value?.title} × ${preview.value?.quantity}`)
const discountLabel = computed(() =>
	props.values.discount_type === "Percentage" && props.values.discount_percentage
		? `Discount (${props.values.discount_percentage}%)`
		: "Discount",
)
const hasDiscount = computed(() => !!preview.value?.discount)
const discountAmount = computed(() =>
	hasDiscount.value ? `−${money(preview.value?.discount ?? 0)}` : money(0),
)
const offerName = computed(() =>
	isCode.value
		? props.values.code.trim().toUpperCase() || "YOURCODE"
		: props.values.code.trim() || "Your offer",
)
</script>

<template>
	<p v-if="!preview" class="text-sm text-ink-gray-5">
		Pick a paid ticket type to preview checkout.
	</p>

	<div v-else-if="compact" class="border-t border-outline-gray-1 bg-surface-gray-1">
		<!-- Same collapse as Limits & schedule: rows grow from 0fr, faster on close. -->
		<div
			class="grid transition-[grid-template-rows] ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
			:class="expanded ? 'grid-rows-[1fr] duration-200' : 'grid-rows-[0fr] duration-150'"
			:inert="!expanded"
		>
			<div class="overflow-hidden">
				<div class="space-y-2 border-b border-outline-gray-1 p-4 text-sm">
					<div class="flex justify-between text-ink-gray-8">
						<span>{{ line }}</span
						><span class="tabular-nums">{{ money(preview.subtotal) }}</span>
					</div>
					<div class="flex justify-between text-ink-green-7">
						<span>{{ discountLabel }} · {{ offerName }}</span>
						<span class="tabular-nums">{{ discountAmount }}</span>
					</div>
				</div>
			</div>
		</div>
		<button
			type="button"
			class="flex w-full items-center gap-2 px-4 py-3 text-left"
			:aria-expanded="expanded"
			@click="expanded = !expanded"
		>
			<Icon icon="lucide-shopping-bag" class="size-4 text-ink-gray-5" />
			<span class="flex-1 truncate text-sm text-ink-gray-6">{{ line }}</span>
			<span v-if="preview.discount" class="text-sm tabular-nums text-ink-gray-4 line-through">
				{{ money(preview.subtotal) }}
			</span>
			<span class="text-base font-semibold tabular-nums text-ink-gray-9">{{
				money(preview.total)
			}}</span>
			<Icon
				icon="lucide-chevron-up"
				class="size-4 text-ink-gray-5 transition-transform duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
				:class="{ 'rotate-180': expanded }"
			/>
		</button>
	</div>

	<div v-else class="space-y-3">
		<div class="flex items-center justify-between gap-2">
			<p class="text-xs text-ink-gray-5">Checkout preview</p>
			<TabButtons
				v-if="currencies.length > 1"
				:model-value="preview.currency"
				:options="currencies.map((currency) => ({ label: currency, value: currency }))"
				@update:model-value="pick.currency = String($event)"
			/>
		</div>

		<div
			class="overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-elevation-1 shadow-sm"
		>
			<div v-if="eligible.length > 1" class="px-2 pt-2">
				<TabButtons
					variant="ghost"
					:model-value="preview.ticketType"
					:options="eligible.map((row) => ({ label: row.title, value: row.name }))"
					@update:model-value="pick.ticketType = String($event)"
				/>
			</div>

			<div class="flex flex-col gap-2.5 px-3.5 pb-1 pt-3.5 text-sm">
				<div class="flex justify-between gap-2 text-ink-gray-8">
					<span>{{ line }}</span>
					<span class="tabular-nums">{{ money(preview.subtotal) }}</span>
				</div>
				<div
					v-if="isCode"
					class="flex h-[30px] items-center gap-1.5 rounded-3 bg-surface-gray-2 pl-2.5 pr-1.5"
				>
					<Icon icon="lucide-ticket-percent" class="size-3.5 shrink-0 text-ink-gray-5" />
					<span
						class="flex-1 truncate font-mono text-xs font-semibold tracking-wider text-ink-gray-9"
					>
						{{ offerName }}
					</span>
					<span class="text-xs" :class="hasDiscount ? 'text-ink-green-7' : 'text-ink-gray-5'">
						{{ hasDiscount ? "Applied" : "Not set" }}
					</span>
				</div>
				<div
					v-else
					class="flex h-[30px] items-center gap-1.5 rounded-3 px-2.5 text-xs transition-colors duration-200 ease-out"
					:class="
						hasDiscount
							? 'bg-surface-green-1 text-ink-green-7'
							: 'bg-surface-gray-2 text-ink-gray-5'
					"
				>
					<Icon icon="lucide-zap" class="size-3 shrink-0" />
					<span class="truncate">
						{{
							hasDiscount ? `${offerName} applied automatically` : `${offerName} will appear here`
						}}
					</span>
				</div>
				<div class="flex justify-between gap-2 text-ink-green-7">
					<span>{{ discountLabel }}</span>
					<span class="tabular-nums">{{ discountAmount }}</span>
				</div>
			</div>

			<div
				class="mt-2 flex items-baseline justify-between border-t border-outline-gray-1 px-3.5 py-3"
			>
				<span class="text-base font-semibold text-ink-gray-9">Total</span>
				<span class="flex items-baseline gap-1.5">
					<span v-if="hasDiscount" class="text-sm tabular-nums text-ink-gray-4 line-through">
						{{ money(preview.subtotal) }}
					</span>
					<span class="text-lg font-semibold tabular-nums text-ink-gray-9">{{
						money(preview.total)
					}}</span>
				</span>
			</div>
		</div>

		<p v-if="preview.note" class="text-xs text-ink-gray-5 text-pretty">{{ preview.note }}</p>
	</div>
</template>
