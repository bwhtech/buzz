<script setup lang="ts">
import { useResizeObserver } from "@vueuse/core"
import { Button } from "frappe-ui"
import { Editor, EditorContent, EditorFixedMenu } from "frappe-ui/editor"
import { nextTick, ref, watch } from "vue"

import {
	Drawer,
	DrawerCloseButton,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import { richTextExtensions, richTextToolbar } from "@/utils/richTextEditor"

const about = defineModel<string>({ required: true })

const box = ref<HTMLElement>()
const focused = ref(false)
const overflowing = ref(false)
const expanded = ref(false)

// The toolbar's own menus render in a portal, so focus moving into one is still editing.
function onFocusOut(event: FocusEvent) {
	const target = event.relatedTarget as Element | null
	if (box.value?.contains(target) || target?.closest("[data-reka-popper-content-wrapper]")) return
	focused.value = false
}

function measure() {
	const content = box.value?.querySelector<HTMLElement>(".ProseMirror")
	if (content) overflowing.value = content.scrollHeight > content.clientHeight + 4
}

useResizeObserver(box, measure)
watch([about, focused], () => nextTick().then(measure))
</script>

<template>
	<div
		ref="box"
		class="overflow-hidden rounded-4 border transition-colors duration-150 ease motion-reduce:transition-none"
		:class="focused ? 'border-outline-gray-4' : 'border-outline-gray-2'"
		@focusin="focused = true"
		@focusout="onFocusOut"
	>
		<Editor
			v-model="about"
			:extensions="richTextExtensions"
			placeholder="What is this event about?"
		>
			<!-- Fades in rather than popping, since it pushes the text down as it appears. -->
			<Transition
				enter-active-class="transition-opacity duration-150 ease-[cubic-bezier(0.23,1,0.32,1)]"
				enter-from-class="opacity-0"
			>
				<EditorFixedMenu
					v-show="focused"
					:items="richTextToolbar"
					class="overflow-x-auto border-b border-outline-gray-1 px-2 py-1"
				/>
			</Transition>
			<EditorContent
				class="prose-sm min-h-30 max-w-none p-3 text-ink-gray-8 transition-[max-height] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] focus:outline-none motion-reduce:transition-none"
				:class="[
					focused ? 'max-h-[30rem] overflow-y-auto' : 'max-h-52 overflow-hidden',
					{
						'[mask-image:linear-gradient(to_bottom,#000_55%,transparent)]': overflowing && !focused,
					},
				]"
			/>
		</Editor>
		<div class="flex justify-end border-t border-outline-gray-1 px-1.5 py-1">
			<Button
				variant="ghost"
				icon-left="lucide-maximize-2"
				:label="__('Expand')"
				@click="expanded = true"
			/>
		</div>
	</div>

	<Drawer v-model:open="expanded" swipe-direction="right">
		<DrawerContent size="lg">
			<div
				class="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-outline-gray-1 pl-5 pr-2.5"
			>
				<DrawerTitle class="text-sm text-ink-gray-8">{{ __("About") }}</DrawerTitle>
				<DrawerDescription class="sr-only">
					{{ __("What the event is about, shown first on its page.") }}
				</DrawerDescription>
				<DrawerCloseButton />
			</div>
			<div class="flex flex-1 flex-col overflow-y-auto overscroll-contain px-7 py-6">
				<p class="mb-5 border-b border-outline-gray-1 pb-4 text-sm text-ink-gray-5">
					{{ __("Always shown first on your event page") }}
				</p>
				<div
					class="overflow-hidden rounded-4 border border-outline-gray-2 focus-within:border-outline-gray-4"
				>
					<Editor
						v-model="about"
						:extensions="richTextExtensions"
						placeholder="What is this event about?"
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
			</div>
			<template #footer>
				<span class="text-sm text-ink-gray-5">{{ __("Saved with the event details") }}</span>
				<Button class="ml-auto" variant="solid" :label="__('Done')" @click="expanded = false" />
			</template>
		</DrawerContent>
	</Drawer>
</template>
