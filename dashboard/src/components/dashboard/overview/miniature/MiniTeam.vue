<script setup lang="ts">
// The people who run the event and their roles. Empty: you alone, and an invite field.
const props = defineProps<{ done: boolean }>()

const PEOPLE = [
	{ name: "Asha Rao", initials: "AR", role: "Host" },
	{ name: "Riya Shah", initials: "RS", role: "Co-host" },
	{ name: "Kabir Mehta", initials: "KM", role: "Check-in" },
]
</script>

<template>
	<div class="mini-panel divide-y divide-outline-gray-1">
		<div
			v-for="person in props.done ? PEOPLE : PEOPLE.slice(0, 1)"
			:key="person.name"
			class="flex items-center gap-2 px-2.5 py-2"
		>
			<span
				class="grid size-5 place-items-center rounded-full bg-surface-gray-3 text-[9px] font-medium text-ink-gray-7"
				>{{ person.initials }}</span
			>
			<span class="flex-1 truncate font-medium">{{ person.name }}</span>
			<span class="mini-value">{{ person.role }}</span>
		</div>
		<div v-if="!props.done" class="p-2">
			<span class="mini-field mini-empty">name@team.com</span>
		</div>
	</div>
</template>
