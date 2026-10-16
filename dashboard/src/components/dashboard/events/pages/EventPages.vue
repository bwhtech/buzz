<script setup lang="ts">
import { Badge, Button, Dialog, Dropdown, ErrorMessage, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"

import EventPageDrawer from "@/components/dashboard/events/pages/EventPageDrawer.vue"
import EventPageRow from "@/components/dashboard/events/pages/EventPageRow.vue"
import {
	blankPageIcon,
	type EventPageTemplate,
	eventPageTemplates,
} from "@/components/dashboard/events/pages/eventPageTemplates"
import { useEventPages } from "@/data/events"
import type { AdditionalEventPage } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ event: string }>()

const pages = useEventPages(props.event)

// Held locally so a drag lands at once; the server order replaces it once every write is in.
const order = ref<AdditionalEventPage[]>([])
const reordering = ref(false)
watch(
	() => pages.data,
	(data) => !reordering.value && (order.value = [...(data ?? [])]),
	{ immediate: true },
)

const titles = computed(() => new Set(order.value.map((page) => page.title)))
const nextDisplayOrder = computed(
	() => Math.max(0, ...order.value.map((page) => page.display_order ?? 0)) + 1,
)

const drawerOpen = ref(false)
const selected = ref<Partial<AdditionalEventPage>>({})

function edit(page: Partial<AdditionalEventPage>) {
	selected.value = page
	drawerOpen.value = true
}

function addFrom(template: Pick<EventPageTemplate, "title" | "content">) {
	edit({ title: template.title, content: template.content, display_order: nextDisplayOrder.value })
}

const addOptions = computed(() => [
	{
		group: "",
		hideLabel: true,
		options: eventPageTemplates.map((template) => ({
			label: template.title,
			icon: template.icon,
			description: titles.value.has(template.title) ? __("Added") : template.description,
			disabled: titles.value.has(template.title),
			onClick: () => addFrom(template),
		})),
	},
	{
		group: "",
		hideLabel: true,
		options: [
			{
				label: __("Blank page"),
				icon: blankPageIcon,
				description: __("Start from an empty page"),
				onClick: () => addFrom({ title: "", content: "" }),
			},
		],
	},
])

// A switch flip shows at once; the stored row only catches up when the write lands.
const toggled = ref<Record<string, boolean>>({})

function isPublished(page: AdditionalEventPage) {
	return toggled.value[page.name] ?? Boolean(page.is_published)
}

async function togglePublished(page: AdditionalEventPage) {
	toggled.value[page.name] = !isPublished(page)
	await pages.setValue
		.submit({ name: page.name, is_published: toggled.value[page.name] ? 1 : 0 })
		.catch(() => null)
	delete toggled.value[page.name]
	if (pages.setValue.error) toast.error(serverErrorMessage(pages.setValue.error))
}

async function duplicate(page: AdditionalEventPage) {
	await pages.insert
		.submit({
			event: props.event,
			title: __("{0} copy", [page.title]),
			content: page.content,
			display_order: nextDisplayOrder.value,
		})
		.catch(() => null)
	if (pages.insert.error) toast.error(serverErrorMessage(pages.insert.error))
}

async function move(fromIndex: number, toIndex: number) {
	if (toIndex < 0 || toIndex >= order.value.length || fromIndex === toIndex) return
	const reordered = [...order.value]
	reordered.splice(toIndex, 0, ...reordered.splice(fromIndex, 1))
	order.value = reordered
	reordering.value = true
	await Promise.all(
		reordered.map((page, index) =>
			page.display_order === index + 1
				? null
				: pages.setValue.submit({ name: page.name, display_order: index + 1 }).catch(() => null),
		),
	)
	reordering.value = false
	if (pages.setValue.error) toast.error(serverErrorMessage(pages.setValue.error))
	await pages.reload()
}

const draggedIndex = ref<number | null>(null)

function dropAt(index: number) {
	if (draggedIndex.value !== null) move(draggedIndex.value, index)
	draggedIndex.value = null
}

function moveWithArrowKeys(event: KeyboardEvent, index: number) {
	const offset = { ArrowUp: -1, ArrowDown: 1 }[event.key]
	if (!offset) return
	event.preventDefault()
	move(index, index + offset)
}

const pendingDelete = ref<AdditionalEventPage | null>(null)
const confirmingDelete = computed({
	get: () => pendingDelete.value !== null,
	set: (open) => !open && (pendingDelete.value = null),
})

// The drawer hides everything outside it from assistive tech, the confirmation included.
function confirmDeleteFromDrawer() {
	drawerOpen.value = false
	pendingDelete.value = selected.value as AdditionalEventPage
}

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
	<section>
		<div class="mb-3.5">
			<div class="flex items-center gap-2">
				<h2 class="text-base font-semibold text-ink-gray-9">{{ __("Pages") }}</h2>
				<Badge v-if="order.length" :label="String(order.length)" size="sm" />
			</div>
			<p class="mt-0.5 text-p-sm text-ink-gray-5">
				{{ __("Each page appears as a tab next to About on your event page") }}
			</p>
		</div>

		<div v-if="!order.length" class="rounded-4 border border-dashed border-outline-gray-3 p-5">
			<p class="text-base font-medium text-ink-gray-8">{{ __("Add more to your event page") }}</p>
			<p class="mt-1 text-p-sm text-ink-gray-5">
				{{
					__(
						"Start from a template, or a blank page. You can rename, hide or reorder pages anytime.",
					)
				}}
			</p>
			<div class="mt-3.5 flex flex-wrap gap-2">
				<Button
					v-for="template in eventPageTemplates"
					:key="template.title"
					variant="outline"
					:icon-left="template.icon"
					:label="template.title"
					@click="addFrom(template)"
				/>
				<Button
					variant="outline"
					:icon-left="blankPageIcon"
					:label="__('Blank page')"
					@click="addFrom({ title: '', content: '' })"
				/>
			</div>
		</div>

		<ul
			v-else
			class="flex flex-col gap-px overflow-hidden rounded-4 border border-outline-gray-2 bg-outline-gray-1"
		>
			<li
				v-for="(page, index) in order"
				:key="page.name"
				class="flex items-center gap-1 bg-surface-base py-2.5 pl-1 pr-2 transition-colors hover:bg-surface-gray-1"
				:class="{ 'opacity-40': draggedIndex === index }"
				@click="edit(page)"
				@dragover.prevent
				@drop="dropAt(index)"
			>
				<button
					type="button"
					draggable="true"
					class="flex size-7 shrink-0 cursor-grab items-center justify-center rounded-4 text-ink-gray-4 hover:text-ink-gray-7 focus-visible:outline-none focus-visible:focus-ring"
					:aria-label="__('Reorder {0}', [page.title])"
					@click.stop
					@dragstart="draggedIndex = index"
					@dragend="draggedIndex = null"
					@keydown="moveWithArrowKeys($event, index)"
				>
					<span class="lucide-grip-vertical size-4" aria-hidden="true" />
				</button>
				<EventPageRow
					:page="page"
					:published="isPublished(page)"
					:is-first="index === 0"
					:is-last="index === order.length - 1"
					@toggle-published="togglePublished(page)"
					@duplicate="duplicate(page)"
					@move="move(index, index + $event)"
					@delete="pendingDelete = page"
				/>
			</li>
			<li class="bg-surface-base">
				<Dropdown :options="addOptions" align="start">
					<button
						type="button"
						class="flex w-full items-center gap-3 px-3 py-2.5 text-left text-base text-ink-gray-5 transition-colors hover:bg-surface-gray-1 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:focus-ring"
					>
						<span
							class="grid size-8 place-items-center rounded-3 border border-dashed border-outline-gray-3"
						>
							<span class="lucide-plus size-4" aria-hidden="true" />
						</span>
						{{ __("Add page") }}
					</button>
				</Dropdown>
			</li>
		</ul>

		<EventPageDrawer
			v-model:open="drawerOpen"
			:event="event"
			:page="selected"
			:pages="pages"
			@delete="confirmDeleteFromDrawer"
		/>

		<Dialog v-model:open="confirmingDelete" :title="__('Delete page')" size="md">
			<div class="space-y-3">
				<p class="text-p-base text-ink-gray-7">
					{{ __("Removes this tab from the event page.") }}
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
