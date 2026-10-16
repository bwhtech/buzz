<script setup lang="ts">
import { Button, Dialog, ErrorMessage, Switch, toast } from "frappe-ui"
import { computed, ref } from "vue"

import EventPageDrawer from "@/components/dashboard/events/EventPageDrawer.vue"
import { useEventPages } from "@/data/events"
import type { AdditionalEventPage } from "@/types"
import { eventPath } from "@/utils/eventUrl"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ event: string; route?: string | null }>()

const pages = useEventPages(props.event)

function plainText(html: string) {
	// Content is Text Editor HTML; a section shows one line of it, so the tags go.
	return new DOMParser().parseFromString(html || "", "text/html").body.textContent?.trim() ?? ""
}

const rows = computed(() =>
	(pages.data ?? []).map((page) => ({ ...page, preview: plainText(page.content) })),
)

const drawerOpen = ref(false)
const selected = ref<AdditionalEventPage | null>(null)

function edit(page: AdditionalEventPage | null) {
	selected.value = page
	drawerOpen.value = true
}

// The store carries is_published only once the write lands, so a switch bound straight to
// the row would snap back for a frame. The picked value holds until the row catches up —
// then it is dropped, so a later write from the drawer cannot be masked by a stale pick.
const toggled = ref<Record<string, boolean>>({})

function isPublished(page: AdditionalEventPage) {
	return toggled.value[page.name] ?? Boolean(page.is_published)
}

async function setPublished(page: AdditionalEventPage, value: boolean) {
	toggled.value[page.name] = value
	await pages.setValue.submit({ name: page.name, is_published: value ? 1 : 0 }).catch(() => null)
	delete toggled.value[page.name]
}

const pendingDelete = ref<AdditionalEventPage | null>(null)
const confirmingDelete = computed({
	get: () => pendingDelete.value !== null,
	set: (open) => !open && (pendingDelete.value = null),
})

async function remove() {
	const page = pendingDelete.value
	if (!page) return
	await pages.delete.submit({ name: page.name }).catch(() => null)
	if (pages.delete.error) return
	toast.success(__("Page deleted"))
	pendingDelete.value = null
}
</script>

<template>
	<section class="space-y-5">
		<div v-for="page in rows" :key="page.name" class="space-y-2">
			<div class="flex items-center gap-2">
				<!-- flex-1, so every row's switch and trash hold the same lane down the column. -->
				<h2
					class="min-w-0 flex-1 truncate text-sm font-medium uppercase tracking-wide text-ink-gray-5"
				>
					{{ page.title }}
				</h2>
				<Switch :model-value="isPublished(page)" @update:model-value="setPublished(page, $event)">
					<template #label
						><span class="sr-only">{{ __("Published") }}</span></template
					>
				</Switch>
				<!-- The tab only exists on the public page once it is published, so the link
				     appears with it. -->
				<Button
					v-if="route && page.is_published"
					variant="ghost"
					icon="lucide-external-link"
					:link="`${eventPath(route)}/${page.route}`"
					:aria-label="__('Open {0}', [page.title])"
				/>
				<Button
					variant="ghost"
					icon="lucide-trash-2"
					:aria-label="__('Delete {0}', [page.title])"
					@click="pendingDelete = page"
				/>
			</div>

			<button
				type="button"
				class="block w-full rounded-6 border border-outline-gray-2 px-3 py-2 text-left transition-colors duration-150 ease-out hover:border-outline-gray-3 hover:bg-surface-gray-1 active:bg-surface-gray-2 focus-visible:border-outline-gray-4 motion-reduce:transition-none"
				:aria-label="__('Edit {0}', [page.title])"
				@click="edit(page)"
			>
				<span v-if="page.preview" class="line-clamp-2 text-p-sm text-ink-gray-6">
					{{ page.preview }}
				</span>
				<span v-else class="text-p-sm text-ink-gray-4">{{ __("Empty page") }}</span>
			</button>
		</div>

		<div class="flex items-center gap-2">
			<p v-if="!rows.length" class="text-p-sm text-ink-gray-5">
				{{ __("Extra pages for the event site — an FAQ, a code of conduct, travel notes.") }}
			</p>
			<Button
				class="ml-auto shrink-0"
				:label="__('Add page')"
				icon-left="lucide-plus"
				@click="edit(null)"
			/>
		</div>

		<EventPageDrawer v-model:open="drawerOpen" :event="event" :page="selected" :pages="pages" />

		<Dialog v-model:open="confirmingDelete" :title="__('Delete page')" size="md">
			<div class="space-y-3">
				<p class="text-p-base text-ink-gray-7">
					{{ __("Removes this tab from the event page. Its link will stop working.") }}
				</p>
				<ErrorMessage :message="serverErrorMessage(pages.delete.error)" />
			</div>
			<template #actions>
				<div class="flex justify-end gap-2">
					<Button :label="__('Cancel')" @click="pendingDelete = null" />
					<Button
						variant="solid"
						theme="red"
						:label="__('Delete')"
						:loading="pages.delete.loading"
						@click="remove"
					/>
				</div>
			</template>
		</Dialog>
	</section>
</template>
