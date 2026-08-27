<script setup lang="ts">
import { Avatar } from "frappe-ui"

import type { TeamOverview } from "@/types"

defineProps<{ team: TeamOverview }>()
</script>

<template>
	<header class="flex items-center gap-4">
		<Avatar
			:image="team.logo ?? undefined"
			:label="team.team_name"
			shape="square"
			class="size-20 outline outline-1 -outline-offset-1 outline-black/10 dark:outline-white/10"
		/>
		<div class="flex flex-col gap-2">
			<h1 class="text-xl font-semibold text-ink-gray-9">{{ team.team_name }}</h1>
			<p v-if="team.slug" class="text-sm text-ink-gray-5">/{{ team.slug }}</p>
		</div>
	</header>
</template>
