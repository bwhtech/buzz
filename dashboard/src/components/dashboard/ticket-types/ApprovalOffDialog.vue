<script setup lang="ts">
import { Button, Dialog, Select } from "frappe-ui"
import { ref, watch } from "vue"

import type { PendingAction } from "@/types"
import { badgeDotClass } from "@/utils/badgeTheme"

const props = defineProps<{ count: number; loading: boolean }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ confirm: [action: PendingAction] }>()

const OPTIONS = [
	{ label: "Keep them pending", value: "keep", dot: badgeDotClass("amber") },
	{ label: "Approve all", value: "approve", dot: badgeDotClass("green") },
	{ label: "Decline all", value: "decline", dot: badgeDotClass("red") },
]

const action = ref<PendingAction>("keep")
watch(isOpen, (open) => open && (action.value = "keep"))

const dotOf = (value: string | number | undefined) =>
	OPTIONS.find((option) => option.value === value)?.dot
</script>

<template>
	<Dialog
		v-model="isOpen"
		:title="`${count} ${count === 1 ? 'request is' : 'requests are'} still waiting. What should happen to them?`"
	>
		<Select v-model="action" class="w-full" :options="OPTIONS" aria-label="Waiting requests">
			<template #prefix="{ selectedOption }">
				<span class="size-2 shrink-0 rounded-full" :class="dotOf(selectedOption?.value)" />
			</template>
			<template #item-prefix="{ item }">
				<span class="size-2 shrink-0 rounded-full" :class="dotOf(item.value)" />
			</template>
		</Select>

		<template #actions="{ close }">
			<div class="flex gap-2">
				<Button
					variant="solid"
					label="Confirm"
					:loading="loading"
					@click="emit('confirm', action)"
				/>
				<Button variant="outline" label="Cancel" @click="close" />
			</div>
		</template>
	</Dialog>
</template>
