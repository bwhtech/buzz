<script setup lang="ts">
import { Button, ErrorMessage, Skeleton, TabList, TabPanel, Tabs, TabTrigger } from "frappe-ui"
import { ref } from "vue"
import { useRoute } from "vue-router"

import SaveActions from "@/components/dashboard/teams/SaveActions.vue"
import TeamDisplaySettings from "@/components/dashboard/teams/settings/TeamDisplaySettings.vue"
import TeamOptionsSettings from "@/components/dashboard/teams/settings/TeamOptionsSettings.vue"
import TeamPageHeader from "@/components/dashboard/teams/TeamPageHeader.vue"
import { useSaveShortcut } from "@/composables/useSaveShortcut"
import { useTeamSettings } from "@/composables/useTeamSettings"
import { serverErrorMessage } from "@/utils/serverError"
import { openTeamPage } from "@/utils/teamUrl"

const route = useRoute()
const settings = useTeamSettings(route.params.teamId as string)

useSaveShortcut(settings.save, () => settings.isDirty)

const tab = ref("display")
const sections = [
	{ value: "display", label: "Display", icon: "lucide-palette" },
	{ value: "options", label: "Options", icon: "lucide-sliders-horizontal" },
]
</script>

<template>
	<TeamPageHeader section="Settings">
		<!-- The saved address, not the one being typed: an unsaved slug is not live yet. -->
		<Button
			v-if="settings.overview.data?.is_published && settings.overview.data.slug"
			class="max-md:hidden"
			:label="__('Team Page')"
			icon-right="lucide-arrow-up-right"
			@click="openTeamPage(settings.overview.data.slug)"
		/>
		<SaveActions
			:is-dirty="settings.isDirty"
			:saving="settings.saving"
			@save="settings.save"
			@discard="settings.discard"
		/>
	</TeamPageHeader>

	<div class="m-auto flex w-full max-w-screen-lg flex-col gap-6 px-4 py-8 max-md:pb-24">
		<ErrorMessage
			v-if="settings.overview.error || settings.error"
			:message="serverErrorMessage(settings.overview.error || settings.error)"
		/>

		<Skeleton
			v-if="!settings.overview.data && !settings.overview.error"
			class="h-64 w-full rounded-5"
		/>

		<Tabs
			v-else-if="settings.overview.data"
			v-model="tab"
			vertical
			class="flex gap-8 max-md:flex-col"
		>
			<TabList variant="ghost" class="w-44 shrink-0">
				<TabTrigger
					v-for="section in sections"
					:key="section.value"
					:value="section.value"
					:label="__(section.label)"
					:icon-left="section.icon"
				/>
			</TabList>
			<TabPanel value="display" class="min-w-0 flex-1 focus:outline-none">
				<TeamDisplaySettings :settings="settings" />
			</TabPanel>
			<TabPanel value="options" class="min-w-0 flex-1 focus:outline-none">
				<TeamOptionsSettings :settings="settings" />
			</TabPanel>
		</Tabs>
	</div>
</template>
