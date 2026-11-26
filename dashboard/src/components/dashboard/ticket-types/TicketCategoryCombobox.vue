<script setup lang="ts">
import { Combobox, toast, useNewDoc } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import type { TicketCategoryItem } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

// Type to find a category; a name that matches none can be created on the spot.
// "" is Uncategorized, which is also what clearing the input leaves.
const category = defineModel<string>({ required: true })
const props = defineProps<{ categories: TicketCategoryItem[]; disabled?: boolean }>()
const emit = defineEmits<{ created: [] }>()

const eventId = useRoute().params.eventId as string
const query = ref("")
// Shown until the parent's list reloads with the new category in it.
const created = ref<TicketCategoryItem[]>([])
const creator = useNewDoc<{ name?: string; title: string; event: string }>("Event Ticket Category")

const allCategories = computed(() => [
	...props.categories,
	...created.value.filter((item) => !props.categories.some((known) => known.name === item.name)),
])

const typed = computed(() => query.value.trim())
const matchesNone = computed(
	() =>
		Boolean(typed.value) &&
		!allCategories.value.some((item) => item.title.toLowerCase() === typed.value.toLowerCase()),
)

const options = computed(() => [
	...allCategories.value.map((item) => ({ label: item.title, value: item.name })),
	{
		type: "custom" as const,
		key: "create",
		label: `Create "${typed.value}"`,
		icon: "lucide-plus",
		condition: () => matchesNone.value,
		onClick: () => create(typed.value),
	},
])

async function create(title: string) {
	Object.assign(creator.doc, { title, event: eventId })
	const doc = await creator.submit().catch(() => null)
	if (!doc?.name) {
		toast.error(serverErrorMessage(creator.error) || "Could not create the category")
		return
	}
	created.value.push({ name: doc.name, title, description: null, sort_order: 0 })
	category.value = doc.name
	query.value = ""
	creator.reset()
	emit("created")
}
</script>

<template>
	<Combobox
		v-model:query="query"
		:model-value="category || null"
		:options="options"
		label="Category"
		placeholder="Uncategorized"
		:loading="creator.loading"
		:disabled="disabled"
		open-on-focus
		@update:model-value="category = $event ? String($event) : ''"
	/>
</template>
