<script setup lang="ts">
import { Button, Dialog, ErrorMessage, FormControl, toast } from "frappe-ui"
import { reactive } from "vue"

import { useUpdateTeamTaxDetails } from "@/data/ticketTypes"
import type { FrappeError } from "@/types"

const props = defineProps<{ event: string }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ saved: [] }>()

const details = reactive({ legal_name: "", tax_id: "", billing_address: "" })
const update = useUpdateTeamTaxDetails()

async function save() {
	// submit() resolves on a server error too, so the error is read off the call.
	await update.submit({ event: props.event, ...details }).catch(() => null)
	if (update.error) return
	toast.success("Tax details saved")
	emit("saved")
	isOpen.value = false
}

const message = (error: unknown) => (error as FrappeError | null)?.message
</script>

<template>
	<Dialog v-model="isOpen" size="md" title="Team tax details">
		<form class="space-y-4" @submit.prevent="save">
			<p class="text-p-base text-ink-gray-5">
				These details apply to every event your team hosts and are required to charge tax on
				tickets.
			</p>
			<FormControl
				v-model="details.legal_name"
				label="Legal name"
				required
				placeholder="Acme Events Pvt Ltd"
			/>
			<FormControl
				v-model="details.tax_id"
				label="Tax ID"
				required
				placeholder="22AAAAA0000A1Z5"
				description="GSTIN, VAT number or equivalent."
			/>
			<FormControl
				v-model="details.billing_address"
				type="textarea"
				label="Billing address"
				required
				:rows="3"
			/>
			<ErrorMessage :message="message(update.error)" />
			<Button
				type="submit"
				variant="solid"
				class="w-full"
				label="Save tax details"
				:loading="update.loading"
			/>
		</form>
	</Dialog>
</template>
