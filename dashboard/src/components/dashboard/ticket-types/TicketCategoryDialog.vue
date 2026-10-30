<script setup lang="ts">
import { Button, Dialog, ErrorMessage, FormControl, toast, useDoc, useNewDoc } from "frappe-ui"
import { computed, ref, watch } from "vue"

import type { FrappeError, TicketCategoryItem } from "@/types"

type CategoryValues = { title: string; description: string }

// Adds a ticket category, or edits the one passed in.
const props = defineProps<{ event: string; category: TicketCategoryItem | null }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ saved: [] }>()

const title = ref("")
const description = ref("")
const showErrors = ref(false)

const creator = useNewDoc<CategoryValues & { event: string }>("Event Ticket Category")
const categoryDoc = useDoc<CategoryValues & { name: string }>({
	doctype: "Event Ticket Category",
	name: () => props.category?.name ?? "",
	immediate: false,
})

const saving = computed(() => (props.category ? categoryDoc.setValue : creator))
const invalid = computed(() => !title.value.trim())
const errorMessage = computed(() => (saving.value.error as FrappeError | null)?.message)

watch(isOpen, (open) => open && reset())

function reset() {
	title.value = props.category?.title ?? ""
	description.value = props.category?.description ?? ""
	showErrors.value = false
	creator.reset()
	categoryDoc.setValue.reset()
}

async function submit() {
	if (saving.value.loading) return
	showErrors.value = true
	if (invalid.value) return

	const values = { title: title.value.trim(), description: description.value.trim() }
	if (props.category) {
		await categoryDoc.setValue.submit(values).catch(() => null)
	} else {
		Object.assign(creator.doc, { ...values, event: props.event })
		await creator.submit().catch(() => null)
	}
	if (saving.value.error) return

	toast.success(props.category ? "Category updated" : "Category added")
	emit("saved")
	isOpen.value = false
}
</script>

<template>
	<Dialog v-model="isOpen" :title="category ? 'Edit Category' : 'Add Category'">
		<form novalidate class="space-y-4" @submit.prevent="submit">
			<FormControl
				v-model="title"
				label="Title"
				placeholder="Workshops"
				autocomplete="off"
				required
			/>
			<FormControl
				v-model="description"
				type="textarea"
				label="Description"
				placeholder="Hands-on sessions on the day before the conference"
			/>

			<ErrorMessage :message="showErrors && invalid ? 'Add a title.' : errorMessage" />

			<Button
				type="button"
				variant="solid"
				class="w-full"
				:label="category ? 'Save' : 'Add'"
				:loading="saving.loading"
				@click="submit"
			/>
		</form>
	</Dialog>
</template>
