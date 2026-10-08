<script setup lang="ts">
import { useEventListener } from "@vueuse/core"
import {
	Button,
	ErrorMessage,
	Icon,
	Skeleton,
	TabList,
	TabPanel,
	Tabs,
	TabTrigger,
} from "frappe-ui"
import { ref } from "vue"
import { useRoute } from "vue-router"

import TeamDisplaySettings from "@/components/dashboard/teams/settings/TeamDisplaySettings.vue"
import TeamOptionsSettings from "@/components/dashboard/teams/settings/TeamOptionsSettings.vue"
import TeamPageHeader from "@/components/dashboard/teams/TeamPageHeader.vue"
import { useTeamSettings } from "@/composables/useTeamSettings"
import { serverErrorMessage } from "@/utils/serverError"
import { openTeamPage } from "@/utils/teamUrl"

const route = useRoute()
const settings = useTeamSettings(route.params.teamId as string)

// Leaving the site drops the draft, so it gets the browser's warning; moving between team
// pages unmounts the page and the edits go with it, the same as event Details.
useEventListener(window, "beforeunload", (unload: BeforeUnloadEvent) => {
	if (settings.isDirty) unload.preventDefault()
})

// The page's save takes the shortcut the browser would spend on saving the document.
useEventListener(document, "keydown", (stroke: KeyboardEvent) => {
	if (stroke.key !== "s" || !(stroke.metaKey || stroke.ctrlKey) || stroke.altKey) return
	stroke.preventDefault()
	if (!stroke.repeat) settings.save()
})

const tab = ref("display")
const sections = [
	{ value: "display", label: "Display", icon: "lucide-palette" },
	{ value: "options", label: "Options", icon: "lucide-sliders-horizontal" },
]
</script>

<template>
	<TeamPageHeader section="Settings">
		<!-- These appear mid-edit, so they arrive rather than pop; exit is quicker than entry. -->
		<Transition
			enter-active-class="transition duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
			enter-from-class="opacity-0 translate-y-1"
			leave-active-class="transition duration-100 ease-out motion-reduce:transition-none"
			leave-to-class="opacity-0"
		>
			<div v-if="settings.isDirty" class="flex items-center gap-2">
				<Button :label="__('Discard')" @click="settings.discard" />
				<Button
					variant="solid"
					:label="__('Save')"
					:loading="settings.saving"
					@click="settings.save"
				/>
			</div>
		</Transition>
	</TeamPageHeader>

	<div class="m-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-8 max-md:pb-24">
		<header class="hidden items-center justify-between gap-3 md:flex">
			<div class="flex items-center gap-3">
				<div class="rounded-4 bg-surface-gray-3 p-2">
					<Icon name="lucide-settings" class="size-6" />
				</div>
				<h1 class="text-4xl font-semibold">{{ __("Settings") }}</h1>
			</div>
			<!-- The saved address, not the one being typed: an unsaved slug is not live yet. -->
			<Button
				v-if="settings.overview.data?.is_published && settings.overview.data.slug"
				:label="__('Team Page')"
				icon-right="lucide-arrow-up-right"
				@click="openTeamPage(settings.overview.data.slug)"
			/>
		</header>

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
			<TabPanel value="display" class="min-w-0 flex-1">
				<TeamDisplaySettings :settings="settings" />
			</TabPanel>
			<TabPanel value="options" class="min-w-0 flex-1">
				<TeamOptionsSettings :settings="settings" />
			</TabPanel>
		</Tabs>
	</div>
</template>
