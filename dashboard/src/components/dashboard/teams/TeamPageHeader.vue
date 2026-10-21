<script setup lang="ts">
import { Breadcrumbs, Button, PageHeader, PageHeaderMobile, PageHeaderMobileTitle } from "frappe-ui"
import { computed } from "vue"
import { type RouteLocationRaw, useRoute } from "vue-router"

import { useIsMobile } from "@/composables/useIsMobile"
import { teamLabel, teams } from "@/data/teams"
import { userResource } from "@/data/user"
import { profileUrl, teamUrl } from "@/utils/teamUrl"

const props = defineProps<{
	section: string
	detail?: string
	back?: RouteLocationRaw
	dirty?: boolean
}>()

const isMobile = useIsMobile()
const route = useRoute()

const team = computed(() => teams.value.find((option) => option.name === route.params.teamId))
const teamName = computed(() => (team.value ? teamLabel(team.value) : ""))
const pageUrl = computed(() => {
	if (props.dirty || !team.value) return null
	const username = userResource.data?.username
	if (team.value.is_personal) return username ? profileUrl(username) : null
	return team.value.is_published && team.value.slug ? teamUrl(team.value.slug) : null
})

// A plain navigation, not a router one: the page is served outside the SPA's /b base.
function openPage() {
	if (pageUrl.value) window.open(pageUrl.value, "_blank", "noopener")
}

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
				v-if="pageUrl"
				variant="ghost"
				icon="lucide-arrow-up-right"
				:label="__('View Page')"
				:tooltip="__('View Page')"
				@click="openPage"
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
				:label="__('View Page')"
				icon-right="lucide-arrow-up-right"
				:disabled="!pageUrl"
				:tooltip="pageUrl ? undefined : __('Publish the community to open its page')"
				@click="openPage"
			/>
		</div>
	</PageHeader>
</template>
