<script setup lang="ts">
import { Button, ErrorMessage, Skeleton, TabList, TabPanel, Tabs, TabTrigger } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import SaveActions from "@/components/dashboard/teams/SaveActions.vue"
import TeamDisplaySettings from "@/components/dashboard/teams/settings/TeamDisplaySettings.vue"
import TeamOptionsSettings from "@/components/dashboard/teams/settings/TeamOptionsSettings.vue"
import TeamPageHeader from "@/components/dashboard/teams/TeamPageHeader.vue"
import { useIsMobile } from "@/composables/useIsMobile"
import { useSaveShortcut } from "@/composables/useSaveShortcut"
import { useTeamSettings } from "@/composables/useTeamSettings"
import { serverErrorMessage } from "@/utils/serverError"

const route = useRoute()
const settings = useTeamSettings(route.params.teamId as string)

useSaveShortcut(settings.save, () => settings.isDirty)

const sections = [
	{ value: "display", label: "Display", icon: "lucide-palette" },
	{ value: "options", label: "Options", icon: "lucide-sliders-horizontal" },
]

const router = useRouter()
const isMobile = useIsMobile()

// The section lives in the URL. On a phone, no section means the list of sections.
const section = computed(() => route.params.section as string | undefined)
const sectionRoute = (value?: string) => ({
	name: "team-settings",
	params: { teamId: route.params.teamId, section: value },
})

// The desktop tabs keep the plain /settings path, so the sidebar item stays active.
const selectedTab = ref("display")
const tab = computed({
	get: () => section.value || selectedTab.value,
	set: (value) => {
		selectedTab.value = value
		if (section.value) router.replace(sectionRoute(value))
	},
})
const openSection = (value: string) => isMobile.value && router.push(sectionRoute(value))

const showList = computed(() => !isMobile.value || !section.value)
const showSection = computed(() => !isMobile.value || Boolean(section.value))
const sectionLabel = computed(() => sections.find((item) => item.value === section.value)?.label)
</script>

<template>
	<TeamPageHeader
		section="Settings"
		team-page-link
		:dirty="settings.isDirty"
		:detail="isMobile && sectionLabel ? __(sectionLabel) : undefined"
		:back="isMobile && section ? sectionRoute() : undefined"
	>
		<SaveActions
			:is-dirty="settings.isDirty"
			:saving="settings.saving"
			:disabled="settings.slugTaken"
			@save="settings.save"
			@discard="settings.discard"
		/>
		<template #leading>
			<Button v-if="settings.isDirty" :label="__('Discard')" @click="settings.discard" />
		</template>
	</TeamPageHeader>

	<div class="m-auto flex w-full max-w-screen-lg flex-col gap-6 px-4 py-8 max-md:pb-24 max-md:pt-4">
		<ErrorMessage
			v-if="settings.overview.error || settings.error"
			:message="serverErrorMessage(settings.overview.error || settings.error)"
		/>

		<Skeleton
			v-if="!settings.overview.data && !settings.overview.error"
			class="h-64 w-full rounded-5"
		/>

		<Tabs v-if="settings.overview.data" v-model="tab" vertical class="flex gap-8 max-md:flex-col">
			<TabList
				variant="ghost"
				class="w-44 shrink-0 max-md:w-full max-md:[&>div:first-child]:hidden max-md:[&_[role=tab]]:h-10 max-md:[&_[role=tab]>span>:last-child]:ms-auto max-md:[&_[role=tab]_*]:!text-ink-gray-8"
				:class="showList ? isMobile && 'enter-from-left' : 'hidden'"
			>
				<TabTrigger
					v-for="item in sections"
					:key="item.value"
					:value="item.value"
					:label="__(item.label)"
					:icon-left="item.icon"
					@click="openSection(item.value)"
				>
					<template v-if="isMobile" #suffix>
						<span class="lucide-chevron-right size-4 text-ink-gray-5" aria-hidden="true" />
					</template>
				</TabTrigger>
			</TabList>
			<TabPanel
				value="display"
				class="min-w-0 flex-1 focus:outline-none"
				:class="showSection ? isMobile && 'enter-from-right' : 'hidden'"
			>
				<TeamDisplaySettings :settings="settings" />
			</TabPanel>
			<TabPanel
				value="options"
				class="min-w-0 flex-1 focus:outline-none"
				:class="showSection ? isMobile && 'enter-from-right' : 'hidden'"
			>
				<TeamOptionsSettings :settings="settings" />
			</TabPanel>
		</Tabs>
	</div>
</template>

<style scoped>
.enter-from-right,
.enter-from-left {
	transition:
		opacity 200ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}

@starting-style {
	.enter-from-right {
		opacity: 0;
		transform: translateX(12px);
	}

	.enter-from-left {
		opacity: 0;
		transform: translateX(-12px);
	}
}

@media (prefers-reduced-motion: reduce) {
	.enter-from-right,
	.enter-from-left {
		transform: none;
	}
}
</style>
