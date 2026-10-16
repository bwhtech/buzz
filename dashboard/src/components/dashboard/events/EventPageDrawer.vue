<script setup lang="ts">
import { Button, ErrorMessage, FormControl, Switch, toast } from "frappe-ui"
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

const props = defineProps<{
	event: string
	page: AdditionalEventPage | null
	pages: EventPagesList
}>()

const open = defineModel<boolean>("open", { required: true })

const isNew = computed(() => !props.page)

const form = reactive({ title: "", content: "", is_published: false })

// Re-seeded on every open, so the drawer never shows the last page's words.
watch(open, (isOpen) => {
	if (!isOpen) return
	Object.assign(form, {
		title: props.page?.title ?? "",
		content: props.page?.content ?? "",
		is_published: Boolean(props.page?.is_published),
	})
})

const isDirty = computed(() => {
	const page = props.page
	if (!page) return true
	return (
		form.title !== page.title ||
		form.content !== (page.content ?? "") ||
		form.is_published !== Boolean(page.is_published)
	)
})

const canSave = computed(
	() => isDirty.value && Boolean(form.title.trim()) && Boolean(form.content.trim()),
)

// One write at a time, whichever it is: the drawer reads its loading and error from here.
const write = computed(() => (isNew.value ? props.pages.insert : props.pages.setValue))

async function save() {
	const values: Partial<AdditionalEventPage> = {
		title: form.title.trim(),
		content: form.content,
		is_published: form.is_published ? 1 : 0,
	}
	const page = props.page
	await (
		page
			? props.pages.setValue.submit({ ...values, name: page.name })
			: props.pages.insert.submit({ ...values, event: props.event })
	).catch(() => null)
	if (write.value.error) return
	toast.success(page ? __("Page saved") : __("Page added"))
	open.value = false
}
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent size="md">
			<div class="flex items-center gap-1 p-4 pb-0">
				<DrawerCloseButton />
				<DrawerTitle class="ml-1 truncate text-lg font-semibold text-ink-gray-9">
					{{ isNew ? __("New page") : __("Edit page") }}
				</DrawerTitle>
				<DrawerDescription class="sr-only">
					{{ __("An extra tab on the event's public page.") }}
				</DrawerDescription>
			</div>

			<div class="flex flex-1 flex-col gap-5 overflow-y-auto overscroll-contain p-4">
				<FormControl
					v-model="form.title"
					:label="__('Title')"
					placeholder="Code of conduct"
					required
					:description="__('Names the tab on the event page.')"
				/>

				<div class="flex items-start justify-between gap-4">
					<div class="space-y-0.5">
						<span class="text-base text-ink-gray-8">{{ __("Published") }}</span>
						<p class="text-p-sm text-ink-gray-5">
							{{ __("Show this tab on the event page.") }}
						</p>
					</div>
					<Switch v-model="form.is_published">
						<template #label
							><span class="sr-only">{{ __("Published") }}</span></template
						>
					</Switch>
				</div>

				<div class="space-y-1.5">
					<!-- The doctype requires content, so the label says so rather than letting the
					     Save button sit disabled with no reason given. -->
					<span class="text-xs text-ink-gray-5">
						{{ __("Content") }}
						<span class="text-ink-red-6" aria-hidden="true">*</span>
					</span>
					<!-- Same box as the About editor: bordered, fixed height, the menu pinned above. -->
					<div
						class="overflow-hidden rounded-6 border border-outline-gray-2 transition-colors duration-150 ease-out focus-within:border-outline-gray-4 motion-reduce:transition-none"
					>
						<Editor
							v-model="form.content"
							:extensions="richTextExtensions"
							:placeholder="__('What should this page say?')"
						>
							<EditorFixedMenu
								:items="richTextToolbar"
								class="overflow-x-auto border-b border-outline-gray-2 px-2 py-1"
							/>
							<EditorContent
								class="prose-sm h-64 max-w-none overflow-y-auto p-3 text-ink-gray-8 focus:outline-none"
							/>
						</Editor>
					</div>
				</div>

				<ErrorMessage :message="serverErrorMessage(write.error)" />
			</div>

			<template #footer>
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
