<script setup lang="ts">
import { Button, Tooltip } from "frappe-ui"
import { computed, ref, watch } from "vue"

import type { ActivityEntry } from "@/types"

const props = defineProps<{
	entry: ActivityEntry
	names: Record<string, string>
	posted: string
	exactTime: string
	// An earlier email in a thread starts folded to its first line.
	folded?: boolean
}>()

const open = ref(!props.folded)
// A newer email in the same direction folds this one.
watch(
	() => props.folded,
	(folded) => (open.value = !folded),
)
const showQuoted = ref(false)

const people = (emails: string[]) => emails.map((email) => props.names[email] || email).join(", ")

function fileSize(bytes: number) {
	return bytes >= 1024 * 1024
		? `${(bytes / 1024 / 1024).toFixed(1)} MB`
		: `${Math.max(1, Math.round(bytes / 1024))} KB`
}

const cue = computed(() =>
	props.entry.received
		? {
				label: "Received",
				icon: "lucide-arrow-down-left",
				tone: "bg-surface-blue-2 text-ink-blue-6",
			}
		: { label: "Sent", icon: "lucide-arrow-up-right", tone: "bg-surface-gray-3 text-ink-gray-6" },
)
</script>

<template>
	<!-- Sent emails sit on gray, replies on white with an outline, so direction reads at a glance. -->
	<div
		class="flex min-w-0 flex-1 flex-col gap-2.5 rounded-5 border px-3.5 py-3"
		:class="
			entry.received
				? 'border-outline-gray-2 bg-surface-base'
				: 'border-transparent bg-surface-gray-1'
		"
	>
		<button
			class="group flex min-w-0 items-center gap-2 text-left"
			:aria-expanded="open"
			@click="open = !open"
		>
			<span class="truncate text-base font-semibold text-ink-gray-9">{{ entry.owner_name }}</span>
			<span
				class="flex size-[18px] shrink-0 items-center justify-center rounded-full"
				:class="cue.tone"
				aria-hidden="true"
			>
				<span :class="cue.icon" class="size-3" />
			</span>
			<span class="shrink-0 text-sm text-ink-gray-5">{{ cue.label }}</span>
			<Tooltip :text="exactTime">
				<time class="ml-auto shrink-0 text-sm text-ink-gray-5" :datetime="entry.creation">
					{{ posted }}
				</time>
			</Tooltip>
			<span
				class="lucide-chevron-down size-3.5 shrink-0 text-ink-gray-5 transition-transform duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none [@media(hover:hover)]:group-hover:text-ink-gray-8"
				:class="open && 'rotate-180'"
				aria-hidden="true"
			/>
		</button>

		<button
			v-if="!open"
			class="reveal truncate text-left text-sm text-ink-gray-6 [@media(hover:hover)]:hover:text-ink-gray-8"
			@click="open = true"
		>
			{{ entry.snippet }}
		</button>

		<div v-else class="reveal flex min-w-0 flex-col gap-3">
			<p class="flex flex-wrap gap-x-3 gap-y-1 text-sm text-ink-gray-5">
				<span>
					{{ entry.received ? "From" : "To" }}
					<span class="text-ink-gray-7">
						{{ entry.received ? entry.owner : people(entry.recipients) }}
					</span>
				</span>
				<span v-if="entry.cc.length">
					Cc <span class="text-ink-gray-7">{{ people(entry.cc) }}</span>
				</span>
			</p>
			<!-- Sanitized by the comments API and Frappe's inbox; replies are rebuilt from escaped text. -->
			<div
				class="max-w-[68ch] text-base leading-[1.6] text-pretty break-words text-ink-gray-8 [&_p+p]:mt-2.5"
				v-html="entry.content"
			/>
			<div v-if="entry.attachments.length" class="flex flex-wrap gap-1.5">
				<Button
					v-for="file in entry.attachments"
					:key="file.url"
					:href="file.url"
					variant="subtle"
					size="xs"
				>
					<template #prefix>
						<span class="lucide-paperclip size-3 text-ink-gray-5" aria-hidden="true" />
					</template>
					<span class="max-w-48 truncate text-ink-gray-6">{{ file.name }}</span>
					<template #suffix>
						<span class="text-ink-gray-5">{{ fileSize(file.size) }}</span>
					</template>
				</Button>
			</div>
			<div v-if="entry.quoted_content" class="flex flex-col gap-2">
				<Button
					class="self-start"
					variant="outline"
					size="sm"
					icon-left="lucide-ellipsis"
					:label="showQuoted ? 'Hide previous message' : 'Show previous message'"
					@click="showQuoted = !showQuoted"
				/>
				<div
					v-if="showQuoted"
					class="reveal max-w-[68ch] border-l-2 border-outline-gray-2 py-0.5 pl-3 text-sm leading-[1.55] text-ink-gray-6 [&_p+p]:mt-1.5"
					v-html="entry.quoted_content"
				/>
			</div>
		</div>
	</div>
</template>
