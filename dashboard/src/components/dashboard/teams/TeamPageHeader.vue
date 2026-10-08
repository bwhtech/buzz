<script setup lang="ts">
import { Breadcrumbs, Button, PageHeader, PageHeaderMobile, PageHeaderMobileTitle } from "frappe-ui"
import { computed } from "vue"
import { type RouteLocationRaw, useRoute } from "vue-router"

import { useIsMobile } from "@/composables/useIsMobile"
import { teams } from "@/data/teams"
import { openTeamPage } from "@/utils/teamUrl"

const props = defineProps<{
	section: string
	detail?: string
	back?: RouteLocationRaw
	dirty?: boolean
}>()

const isMobile = useIsMobile()
const route = useRoute()

const team = computed(() => teams.value.find((option) => option.name === route.params.teamId))
const teamName = computed(() => team.value?.team_name ?? "")
const publicSlug = computed(() =>
	team.value?.is_published && !props.dirty ? team.value.slug : null,
)

const items = computed(() => [{ label: teamName.value || "Community" }, { label: props.section }])
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
					:label="back ? 'Back' : 'Back to communities'"
					:route="back ?? { name: 'communities' }"
				/>
			</slot>
		</template>
		<template #suffix>
			<Button
				v-if="publicSlug"
				variant="ghost"
				icon="lucide-arrow-up-right"
				:label="__('Open community page')"
				:tooltip="__('Open community page')"
				@click="openTeamPage(publicSlug)"
			/>
			<slot />
		</template>
	</PageHeaderMobile>

	<PageHeader v-else class="border-none bg-surface-elevation-1 pt-2">
		<Breadcrumbs :items="items" />
		<div class="flex items-center gap-2">
			<slot />
			<!-- Always shown and always last, so the page's place is known before it is published. -->
			<Button
				variant="ghost"
				:label="__('Community Page')"
				icon-right="lucide-arrow-up-right"
				:disabled="!publicSlug"
				:tooltip="publicSlug ? undefined : __('Publish the community to open its page')"
				@click="publicSlug && openTeamPage(publicSlug)"
			/>
		</div>
	</PageHeader>
</template>
