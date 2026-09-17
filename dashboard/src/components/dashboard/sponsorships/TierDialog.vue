<script setup lang="ts">
import { Button, Dialog, ErrorMessage, FormControl, toast, useDoc, useNewDoc } from "frappe-ui"
import { computed, ref, watch } from "vue"

import type { FrappeError, SponsorshipTierItem } from "@/types"

type TierValues = {
	title: string
	price: number
	currency: string
	enabled: 0 | 1
}
type TierDoc = TierValues & { name: string; event: string }

const props = defineProps<{ event: string; tier: SponsorshipTierItem | null }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ saved: [] }>()

const title = ref("")
const price = ref<number | string>(0)
const currency = ref("INR")
const enabled = ref(true)
const showErrors = ref(false)

const creator = useNewDoc<TierDoc>("Sponsorship Tier")
// Only setValue is used; the tier already arrived with the page.
const editor = useDoc<TierDoc>({
	doctype: "Sponsorship Tier",
	name: () => props.tier?.name ?? "",
	immediate: false,
})
const request = computed(() => (props.tier ? editor.setValue : creator))

const invalid = computed(() => !title.value.trim() || Number(price.value) < 0)
const errorMessage = computed(() =>
	(request.value.error as FrappeError | null)?.messages?.join("\n"),
)

watch(isOpen, (open) => open && reset())

function reset() {
	title.value = props.tier?.title ?? ""
	price.value = props.tier?.price ?? 0
	currency.value = props.tier?.currency || "INR"
	enabled.value = props.tier?.enabled ?? true
	showErrors.value = false
	creator.reset()
	editor.setValue.reset()
}

function values(): TierValues {
	return {
		title: title.value.trim(),
		price: Number(price.value) || 0,
		currency: currency.value.trim().toUpperCase(),
		enabled: enabled.value ? 1 : 0,
	}
}

async function submit() {
	showErrors.value = true
	if (invalid.value) return

	if (props.tier) {
		await editor.setValue.submit(values())
	} else {
		Object.assign(creator.doc, { ...values(), event: props.event })
		await creator.submit().catch(() => null)
	}
	if (request.value.error) return

	toast.success(props.tier ? "Tier updated" : "Tier added")
	emit("saved")
	isOpen.value = false
}
</script>

<template>
	<Dialog v-model="isOpen" :title="tier ? 'Edit tier' : 'Add tier'">
		<form novalidate class="space-y-4" @submit.prevent="submit">
			<FormControl v-model="title" label="Title" placeholder="Gold" autocomplete="off" />

			<div class="grid grid-cols-2 gap-4">
				<FormControl v-model="price" type="number" label="Price" min="0" />
				<FormControl v-model="currency" label="Currency" placeholder="INR" maxlength="3" />
			</div>

			<FormControl
				v-if="tier"
				v-model="enabled"
				type="checkbox"
				label="Enabled"
				description="Disabled tiers stay on existing enquiries and sponsors, but new applicants cannot pick them."
			/>

			<p v-if="showErrors && invalid" class="text-sm text-ink-red-4">
				A tier needs a title and a price of zero or more.
			</p>
			<ErrorMessage v-else-if="errorMessage" :message="errorMessage" />

			<Button
				type="button"
				variant="solid"
				class="w-full"
				:label="tier ? 'Save tier' : 'Add tier'"
				:loading="request.loading"
				@click="submit"
			/>
		</form>
	</Dialog>
</template>
