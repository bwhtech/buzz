<script setup lang="ts">
import { Button, dialog, toast } from "frappe-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"

import EventPageHeader from "@/components/dashboard/events/EventPageHeader.vue"
import { useEventDoc } from "@/data/events"
import PageWithSidebar from "@/layouts/PageWithSidebar.vue"

const route = useRoute()
const eventId = route.params.eventId as string

const event = useEventDoc(() => eventId)

const archived = computed(() => Boolean(event.doc) && !event.doc?.is_published)

// Archiving takes the event off the public site, so it is worth a confirmation. Coming
// back online is not destructive and goes straight through.
function confirmArchive() {
	dialog.confirm({
		title: __("Archive Event"),
		message: __(
			"The event page goes offline and its forms stop accepting responses. You can unarchive it from here at any time.",
		),
		theme: "red",
		confirmLabel: __("Archive"),
		onConfirm: async () => {
			await publish(0)
			// The call settles either way, so the failure has to be rethrown to reach the dialog.
			if (event.setValue.error) throw event.setValue.error
		},
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

	<PageWithSidebar>
		<section class="space-y-3">
			<h1 class="text-xl font-semibold text-ink-gray-9">{{ __("Danger") }}</h1>

			<!-- One row per setting, divided rather than boxed each: the card is the group. -->
			<div class="divide-y divide-outline-gray-1 rounded-6 border border-outline-gray-1">
				<div class="flex flex-wrap items-center justify-between gap-3 p-4">
					<div class="space-y-1">
						<h2 class="font-medium text-ink-gray-8">
							{{ archived ? __("Unarchive event") : __("Archive event") }}
						</h2>
						<p class="text-p-sm text-ink-gray-6">
							{{
								archived
									? __("Puts the event page back online and reopens its forms.")
									: __("Takes the event page offline and stops its forms accepting responses.")
							}}
						</p>
					</div>

					<Button
						v-if="archived"
						:label="__('Unarchive')"
						:loading="event.setValue.loading"
						@click="publish(1)"
					/>
					<Button
						v-else
						theme="red"
						variant="subtle"
						:label="__('Archive')"
						:loading="event.setValue.loading"
						@click="confirmArchive"
					/>
				</div>
			</div>
		</section>
	</PageWithSidebar>
</template>
