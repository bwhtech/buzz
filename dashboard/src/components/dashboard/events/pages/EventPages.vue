<script setup lang="ts">
import { Badge, Button, Dialog, Dropdown, ErrorMessage, ItemListRow, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"

import EventPageDrawer from "@/components/dashboard/events/pages/EventPageDrawer.vue"
import EventPageRow from "@/components/dashboard/events/pages/EventPageRow.vue"
import {
	blankPageIcon,
	type EventPageTemplate,
	eventPageTemplates,
} from "@/components/dashboard/events/pages/eventPageTemplates"
import { useEventPageOrder } from "@/components/dashboard/events/pages/useEventPageOrder"
import { useEventPages } from "@/data/events"
import type { AdditionalEventPage } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

// Read-only rows open nothing: the editor drawer renders outside the page's locked fields.
const props = defineProps<{ event: string; readonly?: boolean }>()

const pages = useEventPages(props.event)

const { order, animateMoves, move, draggedIndex, overIndex, dropAt, endDrag, moveWithArrowKeys } =
	useEventPageOrder(pages)

// A new page can land out of view, so it lights up briefly to show where it went.
const flashedName = ref<string | null>(null)
let flashTimer: ReturnType<typeof setTimeout>
watch(
	() => pages.insert.data?.name,
	(name) => {
		if (!name) return
		flashedName.value = name
		clearTimeout(flashTimer)
		flashTimer = setTimeout(() => (flashedName.value = null), 900)
	},
)

const titles = computed(() => new Set(order.value.map((page) => page.title)))
const nextDisplayOrder = computed(
	() => Math.max(0, ...order.value.map((page) => page.display_order ?? 0)) + 1,
)

const drawerOpen = ref(false)
const selected = ref<Partial<AdditionalEventPage>>({})

function edit(page: Partial<AdditionalEventPage>) {
	if (props.readonly) return
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

		<TransitionGroup
			v-else
			tag="ul"
			class="relative flex flex-col gap-0.5 rounded-4 border border-outline-gray-2 p-1"
			:move-class="
				animateMoves
					? 'transition-transform duration-200 ease-[cubic-bezier(0.77,0,0.175,1)] motion-reduce:transition-none'
					: ''
			"
			enter-active-class="transition-[opacity,transform] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none"
			enter-from-class="translate-y-1 opacity-0 motion-reduce:translate-y-0"
			leave-active-class="absolute inset-x-1 transition-opacity duration-150 ease-[cubic-bezier(0.23,1,0.32,1)]"
			leave-to-class="opacity-0"
		>
			<ItemListRow
				v-for="(page, index) in order"
				:key="page.name"
				as="li"
				size="lg"
				class="relative cursor-pointer !pl-1 active:bg-surface-gray-3 [@media(hover:hover)]:hover:bg-surface-gray-2"
				:class="{
					'opacity-40': draggedIndex === index,
					'!bg-surface-gray-3': flashedName === page.name,
				}"
				@click="edit(page)"
				@dragover.prevent="overIndex = index"
				@drop="dropAt(index)"
			>
				<template #prefix>
					<Button
						variant="ghost"
						icon="lucide-grip-vertical"
						draggable="true"
						class="cursor-grab text-ink-gray-4 active:cursor-grabbing"
						:aria-label="__('Reorder {0}', [page.title])"
						@click.stop
						@dragstart="draggedIndex = index"
						@dragend="endDrag"
						@keydown="moveWithArrowKeys($event, index)"
					/>
				</template>
				<!-- Where the dragged row will land: above this one when moving up, below when down. -->
				<span
					v-if="draggedIndex !== null && overIndex === index && draggedIndex !== index"
					class="pointer-events-none absolute inset-x-2 h-0.5 rounded-full bg-surface-gray-6"
					:class="draggedIndex < index ? '-bottom-0.5' : '-top-0.5'"
					aria-hidden="true"
				/>
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
			</ItemListRow>
			<li key="add">
				<Dropdown :options="addOptions" align="start">
					<Button
						variant="ghost"
						size="md"
						icon-left="lucide-plus"
						:label="__('Add page')"
						class="w-full !justify-start !text-ink-gray-5 hover:!text-ink-gray-8"
					/>
				</Dropdown>
			</li>
		</TransitionGroup>

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
