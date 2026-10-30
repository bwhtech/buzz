<script setup lang="ts">
import { Breadcrumbs, Button, ErrorMessage, Switch, toast } from "frappe-ui"
import { Editor, EditorContent, EditorFixedMenu } from "frappe-ui/editor"
import { computed, reactive, watch } from "vue"

import {
	Drawer,
	DrawerCloseButton,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import type { EventPagesList } from "@/data/events"
import type { AdditionalEventPage } from "@/types"
import { richTextExtensions, richTextToolbar } from "@/utils/richTextEditor"
import { serverErrorMessage } from "@/utils/serverError"

// A page without a name is a new one, seeded from a template or blank.
const props = defineProps<{
	event: string
	page: Partial<AdditionalEventPage>
	pages: EventPagesList
}>()
const emit = defineEmits<{ delete: [] }>()

const open = defineModel<boolean>("open", { required: true })

const isNew = computed(() => !props.page.name)

const form = reactive({ title: "", content: "", is_published: false })

watch(open, (isOpen) => {
	if (!isOpen) return
	Object.assign(form, {
		title: props.page.title ?? "",
		content: props.page.content ?? "",
		is_published: Boolean(props.page.is_published),
	})
})

// The editor stamps table-of-contents ids on headings, which is not an edit.
function withoutHeadingIds(html: string) {
	return html.replace(/ (?:data-toc-id|id)="[^"]*"/g, "")
}

const isDirty = computed(
	() =>
		isNew.value ||
		form.title !== props.page.title ||
		withoutHeadingIds(form.content) !== withoutHeadingIds(props.page.content ?? "") ||
		form.is_published !== Boolean(props.page.is_published),
)

function hasText(html: string) {
	return Boolean(new DOMParser().parseFromString(html, "text/html").body.textContent?.trim())
}

const canSave = computed(() => isDirty.value && Boolean(form.title.trim()) && hasText(form.content))

const crumbs = computed(() => [
	{ label: __("Pages"), onClick: () => (open.value = false) },
	{ label: form.title || __("Untitled page") },
])

const write = computed(() => (isNew.value ? props.pages.insert : props.pages.setValue))

async function save() {
	const values: Partial<AdditionalEventPage> = {
		title: form.title.trim(),
		content: form.content,
		is_published: form.is_published ? 1 : 0,
	}
	const name = props.page.name
	await (
		name
			? props.pages.setValue.submit({ ...values, name })
			: props.pages.insert.submit({
					...values,
					event: props.event,
					display_order: props.page.display_order,
				})
	).catch(() => null)
	if (write.value.error) return
	toast.success(name ? __("Page saved") : __("Page added"))
	open.value = false
}
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="lg">
			<div
				class="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-outline-gray-1 pl-5 pr-2.5"
			>
				<DrawerTitle class="min-w-0">
					<Breadcrumbs :items="crumbs" />
				</DrawerTitle>
				<DrawerDescription class="sr-only">
					{{ __("An extra tab on the event's public page.") }}
				</DrawerDescription>
				<DrawerCloseButton />
			</div>

			<div class="flex flex-1 flex-col overflow-y-auto overscroll-contain px-7 py-6">
				<input
					v-model="form.title"
					:aria-label="__('Title')"
					:placeholder="__('Untitled page')"
					class="w-full border-0 bg-transparent p-0 text-2xl font-semibold text-ink-gray-9 placeholder:text-ink-gray-4 focus:outline-none focus:ring-0"
				/>
				<div
					class="mb-5 mt-2.5 flex items-center justify-between gap-3 border-b border-outline-gray-1 pb-4"
				>
					<span class="text-sm text-ink-gray-5">{{ __("Shows as a tab next to About") }}</span>
					<Switch v-model="form.is_published" :label="__('Show on event page')" size="sm" />
				</div>

				<div
					class="overflow-hidden rounded-4 border border-outline-gray-2 transition-colors duration-150 ease focus-within:border-outline-gray-4 motion-reduce:transition-none"
				>
					<Editor
						v-model="form.content"
						:extensions="richTextExtensions"
						:placeholder="__('Start writing…')"
						autofocus
					>
						<EditorFixedMenu
							:items="richTextToolbar"
							class="overflow-x-auto border-b border-outline-gray-2 px-2 py-1"
						/>
						<EditorContent
							class="prose-sm min-h-80 max-w-none p-3 text-ink-gray-8 focus:outline-none"
						/>
					</Editor>
				</div>

				<ErrorMessage class="mt-3" :message="serverErrorMessage(write.error)" />
			</div>

			<template #footer>
				<Button
					v-if="!isNew"
					variant="ghost"
					theme="red"
					icon-left="lucide-trash-2"
					:label="__('Delete page')"
					@click="emit('delete')"
				/>
				<div class="ml-auto flex items-center gap-2">
					<Button :label="__('Cancel')" @click="open = false" />
					<Button
						variant="solid"
						:label="isNew ? __('Add page') : __('Save')"
						:disabled="!canSave"
						:loading="write.loading"
						@click="save"
					/>
				</div>
			</template>
		</DrawerContent>
	</Drawer>
</template>
