<script setup lang="ts">
import { Button, Dropdown } from "frappe-ui"
import { computed } from "vue"

export interface Recipient {
	name: string
	email: string
}

const props = defineProps<{
	recipients: Recipient[]
	recipientsLabel: string
	size?: "xs" | "sm"
}>()

// True means the note goes out by email instead of staying with the team.
const toRecipients = defineModel<boolean>({ required: true })
// The menu renders in a portal, so the composer cannot see focus inside it.
const open = defineModel<boolean>("open", { default: false })

const names = computed(() => props.recipients.map((person) => person.name).join(", "))
const firstNames = computed(() =>
	props.recipients.map((person) => person.name.split(" ")[0]).join(" and "),
)

const options = computed(() => [
	{
		label: "Team only",
		description: "Only your team sees this note",
		icon: "lucide-lock",
		selected: !toRecipients.value,
		onClick: () => (toRecipients.value = false),
	},
	{
		label: `Email ${props.recipientsLabel}`,
		description: `Sent to ${firstNames.value} by email`,
		icon: "lucide-mail",
		selected: toRecipients.value,
		onClick: () => (toRecipients.value = true),
	},
])
</script>

<template>
	<Dropdown v-model:open="open" :options="options" side="top" align="start">
		<Button
			:size="size"
			:variant="toRecipients ? 'outline' : 'ghost'"
			:icon-left="toRecipients ? 'lucide-mail' : 'lucide-lock'"
			icon-right="lucide-chevron-down"
			class="max-w-72"
		>
			<span class="truncate">{{ toRecipients ? `To ${names}` : "Team only" }}</span>
		</Button>
	</Dropdown>
</template>
