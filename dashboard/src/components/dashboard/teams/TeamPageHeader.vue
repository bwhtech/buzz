<script setup lang="ts">
import { currentTeam } from "@/data/teams";
import { Breadcrumbs, Button, PageHeader } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{ title: string }>();

const items = computed(() => {
	const team = currentTeam.value;
	if (!team) return [{ label: props.title }];
	return [{ label: team.team_name, route: "/manage/team/overview" }, { label: props.title }];
});
</script>

<template>
	<PageHeader class="border-none pt-2 bg-surface-elevation-1">
		<Breadcrumbs :items="items" />
		<Button variant="solid" icon-left="plus" label="Create Event" />
	</PageHeader>
</template>
