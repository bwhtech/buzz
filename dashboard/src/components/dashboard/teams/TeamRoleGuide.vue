<script setup lang="ts">
const ROLES = [
	{ name: "Owner", can: __("Created the team. Full control, and cannot be removed.") },
	{ name: "Admin", can: __("Everything an owner can do, except deleting the team.") },
	{
		name: "Manager",
		can: __("Creates and edits events. Cannot delete records or manage members."),
	},
	{ name: "Frontdesk", can: __("Checks attendees in at the door, and nothing else.") },
	{ name: "Viewer", can: __("Reads the team's events and details. Changes nothing.") },
]
</script>

<template>
	<section class="rounded-7 bg-surface-gray-1 p-4">
		<h4 class="text-sm font-medium text-ink-gray-7">{{ __("What each role can do") }}</h4>
		<dl class="mt-3 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
			<div v-for="role in ROLES" :key="role.name" class="flex gap-2">
				<dt class="w-20 shrink-0 font-medium text-ink-gray-7">{{ role.name }}</dt>
				<dd class="text-ink-gray-5">{{ role.can }}</dd>
			</div>
		</dl>
	</section>
</template>
