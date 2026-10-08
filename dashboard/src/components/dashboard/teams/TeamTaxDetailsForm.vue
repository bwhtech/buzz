<script setup lang="ts">
import { FormControl } from "frappe-ui"

import type { TeamTaxDetails } from "@/types"

defineProps<{ details: Record<keyof TeamTaxDetails, string>; editable: boolean }>()
</script>

<template>
	<section class="space-y-4">
		<div class="space-y-1">
			<h2 class="text-xl font-semibold text-ink-gray-8">{{ __("Tax Details") }}</h2>
			<p class="text-p-sm text-ink-gray-5">
				{{
					editable
						? __("Used on every event your team hosts, and needed to charge tax on tickets.")
						: __("Only owners and admins can change these.")
				}}
			</p>
		</div>
		<div class="flex flex-col gap-4 sm:flex-row">
			<div class="flex flex-1 flex-col gap-4">
				<FormControl
					v-model="details.legal_name"
					:label="__('Legal name')"
					:placeholder="__('Acme Events Pvt Ltd')"
					required
					:disabled="!editable"
				/>
				<FormControl
					v-model="details.tax_id"
					:label="__('Tax ID')"
					:placeholder="__('22AAAAA0000A1Z5')"
					:description="__('GSTIN, VAT number or equivalent.')"
					required
					:disabled="!editable"
				/>
			</div>
			<FormControl
				v-model="details.billing_address"
				type="textarea"
				class="flex-1"
				:label="__('Billing address')"
				:rows="5"
				required
				:disabled="!editable"
			/>
		</div>
	</section>
</template>
