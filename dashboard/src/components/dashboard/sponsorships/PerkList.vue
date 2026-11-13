<script setup lang="ts">
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
			<input
				:value="item"
				type="text"
				:placeholder="placeholder"
				:aria-label="label"
				:disabled="disabled"
				class="min-w-0 flex-1 border-0 bg-transparent px-1 py-1.5 text-base text-ink-gray-8 placeholder:text-ink-gray-4 focus:outline-none focus:ring-0"
				@input="updatePerk(index, ($event.target as HTMLInputElement).value)"
				@keydown.enter.prevent="add"
			/>
		</template>
	</SortableList>
</template>
