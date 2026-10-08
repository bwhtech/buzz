<script setup lang="ts">
import { Button } from "frappe-ui"
import { computed, ref } from "vue"

import EventLinkDialog from "@/components/dashboard/events/EventLinkDialog.vue"
import type { EventExternalLink } from "@/types"
import { hostOf, linkIconClass } from "@/utils/eventLinks"

withDefaults(defineProps<{ hint?: string; headingClass?: string }>(), {
	hint: undefined,
	// The event Details label; a page with section headings passes its own.
	headingClass: "text-sm font-medium uppercase tracking-wide text-ink-gray-5",
})

const links = defineModel<EventExternalLink[]>({ required: true })

const dialogOpen = ref(false)
const editingIndex = ref<number | null>(null)
const editingLink = computed(() =>
	editingIndex.value === null ? null : links.value[editingIndex.value],
)

function open(index: number | null) {
	editingIndex.value = index
	dialogOpen.value = true
}

function commit(link: EventExternalLink) {
	links.value =
		editingIndex.value === null
			? [...links.value, link]
			: links.value.map((existing, index) => (index === editingIndex.value ? link : existing))
}

function remove() {
	links.value = links.value.filter((_, index) => index !== editingIndex.value)
}
</script>

<template>
	<section class="space-y-3">
		<div class="flex items-center justify-between">
			<h2 :class="headingClass">{{ __("Links") }}</h2>
			<Button :label="__('Add')" icon-left="lucide-plus" @click="open(null)" />
		</div>

		<ul v-if="links.length" class="-mx-2 space-y-0.5">
			<li
				v-for="(link, index) in links"
				:key="`${index}-${link.url}`"
				class="group flex items-center gap-1 rounded-4 transition-colors duration-150 ease-out hover:bg-surface-gray-2 motion-reduce:transition-none"
			>
				<button
					type="button"
					class="flex min-w-0 flex-1 items-center gap-3 rounded-4 px-2 py-1.5 text-left active:bg-surface-gray-3"
					:aria-label="__('Edit {0}', [link.label])"
					@click="open(index)"
				>
					<span
						class="flex size-7 shrink-0 items-center justify-center rounded-4 bg-surface-gray-2 text-ink-gray-7 group-hover:bg-surface-gray-3"
					>
						<span :class="[linkIconClass(link.icon), 'size-4']" aria-hidden="true" />
					</span>
					<span class="min-w-0 flex-1">
						<span class="block truncate text-sm text-ink-gray-8">{{ link.label }}</span>
						<span class="block truncate text-xs text-ink-gray-5">{{ hostOf(link.url) }}</span>
					</span>
				</button>
				<Button
					variant="ghost"
					icon="lucide-external-link"
					:link="link.url"
					:aria-label="__('Open {0}', [link.label])"
					class="mr-1 transition-opacity [@media(hover:hover)]:opacity-0 duration-150 ease-out group-hover:opacity-100 focus-visible:opacity-100 motion-reduce:transition-none"
				/>
			</li>
		</ul>

		<p v-else class="text-p-sm text-ink-gray-5">
			{{
				hint ??
				__("Venue map, slides, community chat — anything attendees should have one tap away.")
			}}
		</p>

		<EventLinkDialog v-model="dialogOpen" :link="editingLink" @submit="commit" @remove="remove" />
	</section>
</template>
