<script setup lang="ts">
import { Breadcrumbs, Button, PageHeader, PageHeaderMobile, PageHeaderMobileTitle } from "frappe-ui"
import { computed } from "vue"
import { type RouteLocationRaw, useRoute } from "vue-router"

import { useIsMobile } from "@/composables/useIsMobile"
import { teams } from "@/data/teams"
import { openTeamPage } from "@/utils/teamUrl"

// detail and back are for a sub-page on a phone: its name beside the team, and where back goes.
// teamPageLink: also offer the public page link on desktop, which Settings does.
const props = defineProps<{
	section: string
	detail?: string
	back?: RouteLocationRaw
	teamPageLink?: boolean
	// Unsaved edits own the header's ends, so the page link steps aside.
	dirty?: boolean
}>()

const isMobile = useIsMobile()
const route = useRoute()

const team = computed(() => teams.value.find((option) => option.name === route.params.teamId))
const teamName = computed(() => team.value?.team_name ?? "")
// Only a published team has a page to open.
const publicSlug = computed(() =>
	team.value?.is_published && !props.dirty ? team.value.slug : null,
)

const items = computed(() => [{ label: teamName.value || "Team" }, { label: props.section }])
</script>

<template>
	<PageHeaderMobile v-if="isMobile">
		<PageHeaderMobileTitle>
			{{ teamName }}
			<span v-if="detail" class="text-base font-normal text-ink-gray-5">· {{ detail }}</span>
		</PageHeaderMobileTitle>
		<template #prefix>
			<!-- A page with unsaved edits puts Discard here, as the event pages do. -->
			<slot name="leading">
				<Button
					variant="ghost"
					icon="lucide-chevron-left"
					:label="back ? 'Back' : 'Back to teams'"
					:route="back ?? { name: 'teams' }"
				/>
			</slot>
		</template>
		<template #suffix>
			<Button
				v-if="publicSlug"
				variant="ghost"
				icon="lucide-arrow-up-right"
				:label="__('Open team page')"
				:tooltip="__('Open team page')"
				@click="openTeamPage(publicSlug)"
			/>
			<slot />
		</template>
	</PageHeaderMobile>

	<PageHeader v-else class="border-none bg-surface-elevation-1 pt-2">
		<Breadcrumbs :items="items" />
		<div class="flex items-center gap-2">
			<Button
				v-if="teamPageLink && publicSlug"
				:label="__('Team Page')"
				icon-right="lucide-arrow-up-right"
				@click="openTeamPage(publicSlug)"
			/>
			<slot />
		</div>
	</PageHeader>
</template>
