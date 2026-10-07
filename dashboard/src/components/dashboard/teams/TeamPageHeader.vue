<script setup lang="ts">
import { Breadcrumbs, Button, PageHeader, PageHeaderMobile } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import { useIsMobile } from "@/composables/useIsMobile"
import { teams } from "@/data/teams"

const props = defineProps<{ section: string }>()

const isMobile = useIsMobile()
const route = useRoute()

const teamName = computed(
	() => teams.value.find((team) => team.name === route.params.teamId)?.team_name ?? "",
)

const items = computed(() => [{ label: teamName.value || "Team" }, { label: props.section }])
</script>

<template>
	<PageHeaderMobile v-if="isMobile" :title="teamName">
		<template #prefix>
			<Button
				variant="ghost"
				icon="lucide-chevron-left"
				label="Back to teams"
				:route="{ name: 'teams' }"
			/>
		</template>
		<template #suffix>
			<slot />
		</template>
	</PageHeaderMobile>

	<PageHeader v-else class="border-none bg-surface-elevation-1 pt-2">
		<Breadcrumbs :items="items" />
		<div class="flex items-center gap-2">
			<slot />
		</div>
	</PageHeader>
</template>
