<script setup lang="ts">
import { Button, Skeleton, dialog, toast } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import { useEventDoc } from "@/data/events"

// A settings row and the group it belongs to. The page renders whatever this describes,
// so a new setting is an entry here rather than another block of markup.
type Setting = {
	name: string
	title: string
	description: string
	action: { label: string; theme?: "red"; onClick: () => void }
}

type SettingGroup = { name: string; title: string; settings: Setting[] }

const route = useRoute()
const eventId = route.params.eventId as string

const event = useEventDoc(() => eventId)

// Only read once the doc has landed, so a null doc never renders as "not archived".
const archived = computed(() => !event.doc?.is_published)

const settingGroups = computed<SettingGroup[]>(() => [
	{ name: "danger", title: __("Danger"), settings: [archiveSetting()] },
])

// One row, two directions: which one it offers depends on where the event stands.
function archiveSetting(): Setting {
	if (archived.value)
		return {
			name: "archive",
			title: __("Unarchive event"),
			description: __("Puts the event page back online."),
			action: { label: __("Unarchive"), onClick: () => publish(1) },
		}

	return {
		name: "archive",
		title: __("Archive event"),
		description: __("Takes the event page offline. Its forms will stop accepting responses."),
		action: { label: __("Archive"), theme: "red", onClick: confirmArchive },
	}
}

// Archiving takes the event off the public site, so it is worth a confirmation. Coming
// back online is not destructive and goes straight through.
function confirmArchive() {
	dialog.confirm({
		title: __("Archive Event?"),
		message: __(
			"The event page goes offline and its forms stop accepting responses. You can unarchive it from here at any time.",
		),
		theme: "red",
		confirmLabel: __("Archive"),
		onConfirm: () => publish(0),
	})
}

async function publish(is_published: 0 | 1) {
	await event.setValue.submit({ is_published })
	if (event.setValue.error) {
		// An event that never had a route cannot be published — the server says so.
		toast.error(event.setValue.error.message || __("Could not save the event"))
		return
	}
	toast.success(is_published ? __("Event is back online") : __("Event archived"))
}
</script>

<template>
	<EventPageHeader :title="event.doc?.title" section="More" />

	<div class="m-auto w-full max-w-[800px] space-y-8 px-4 py-8">
		<section v-for="group in settingGroups" :key="group.name" class="space-y-3">
			<h2 class="text-lg font-semibold text-ink-gray-9">{{ group.title }}</h2>

			<!-- One row per setting, divided rather than boxed each: the card is the group. -->
			<div class="overflow-hidden rounded-6 border border-outline-gray-2">
				<div v-if="!event.doc" class="p-4">
					<Skeleton class="h-11 w-full rounded-4" />
				</div>

				<Transition
					enter-active-class="transition-opacity duration-200 ease-out motion-reduce:transition-none"
					enter-from-class="opacity-0"
				>
					<div v-if="event.doc" class="divide-y divide-outline-gray-1">
						<div
							v-for="setting in group.settings"
							:key="setting.name"
							class="flex flex-wrap items-center justify-between gap-3 p-4"
						>
							<div class="space-y-1">
								<h3 class="font-medium text-base text-ink-gray-8">{{ setting.title }}</h3>
								<p class="text-p-sm text-ink-gray-6">{{ setting.description }}</p>
							</div>

							<Button
								:label="setting.action.label"
								:theme="setting.action.theme"
								:loading="event.setValue.loading"
								class="transition-transform duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] active:scale-[0.97] motion-reduce:active:scale-100"
								@click="setting.action.onClick"
							/>
						</div>
					</div>
				</Transition>
			</div>
		</section>
	</div>
</template>
