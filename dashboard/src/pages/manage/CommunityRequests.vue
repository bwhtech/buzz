<script setup lang="ts">
import CommunityQueue from "@/components/dashboard/communities/CommunityQueue.vue"
import CreateEventHeader from "@/components/dashboard/CreateEventHeader.vue"
import { currentTeam } from "@/data/teams"
</script>

<template>
	<CreateEventHeader title="Community" />
	<!-- Keyed by team: switching teams starts a fresh queue for the new community. -->
	<CommunityQueue
		v-if="currentTeam"
		:key="currentTeam.name"
		:community="currentTeam.name"
		:community-name="currentTeam.team_name"
	/>
</template>
