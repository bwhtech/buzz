<script setup lang="ts">
import { TextInput } from "frappe-ui"

import SortableList from "@/components/dashboard/sponsorships/SortableList.vue"

const perks = defineModel<string[]>({ required: true })
withDefaults(
	defineProps<{
		disabled?: boolean
		label?: string
		addLabel?: string
		itemName?: string
		placeholder?: string
	}>(),
	{ label: "Perks", addLabel: "Add perk", itemName: "perk", placeholder: "Describe the perk" },
)

function updatePerk(index: number, value: string) {
	perks.value = perks.value.map((perk, perkIndex) => (perkIndex === index ? value : perk))
}
</script>

<template>
	<SortableList
		v-model="perks"
		:label="label"
		:add-label="addLabel"
		:item-name="itemName"
		:create-item="() => ''"
		:disabled="disabled"
	>
		<template #row="{ item, index, add }">
			<TextInput
				:model-value="item"
				class="min-w-0 flex-1"
				:placeholder="placeholder"
				:aria-label="itemName"
				:disabled="disabled"
				@update:model-value="updatePerk(index, $event)"
				@keydown.enter.prevent="add"
			/>
		</template>
	</SortableList>
</template>
