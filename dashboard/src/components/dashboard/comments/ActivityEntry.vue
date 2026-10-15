<script setup lang="ts">
import { Avatar, Dropdown, dayjsLocal } from "frappe-ui"
import { computed, ref } from "vue"

import { sessionUser } from "@/data/session"
import type { ActivityEntry, TeamMember } from "@/types"

import CommentComposer from "./CommentComposer.vue"

const props = defineProps<{
	entry: ActivityEntry
	last: boolean
	members: TeamMember[]
	// Display names for email addresses, so "Emailed to" reads as people.
	names: Record<string, string>
	createdLabel: string
	saving?: boolean
}>()

const emit = defineEmits<{ update: [content: string]; delete: [] }>()

const editing = ref(false)
const draft = ref("")

const posted = computed(() => dayjsLocal(props.entry.creation))
const isNote = computed(() => props.entry.kind === "comment" || props.entry.kind === "email")
const isAuthor = computed(
	() => props.entry.kind === "comment" && props.entry.owner === sessionUser(),
)
const recipientNames = computed(() =>
	props.entry.recipients.map((email) => props.names[email] || email).join(" and "),
)
const actor = computed(() => (props.entry.owner === "Guest" ? "Someone" : props.entry.owner_name))

const actions = [
	{ label: "Edit", icon: "lucide-pencil", onClick: startEditing },
	{ label: "Delete", icon: "lucide-trash-2", theme: "red" as const, onClick: () => emit("delete") },
]

function startEditing() {
	draft.value = props.entry.content || ""
	editing.value = true
}

function save(content: string) {
	emit("update", content)
	editing.value = false
}
</script>

<template>
	<li class="entry relative flex gap-3" :class="!last && 'pb-6'">
		<!-- The rail runs from under this marker to the next one. -->
		<span
			v-if="!last"
			class="absolute top-8 bottom-1 left-3 w-px bg-surface-gray-3"
			aria-hidden="true"
		/>

		<template v-if="isNote">
			<Avatar
				size="md"
				:label="entry.owner_name"
				:image="entry.owner_image ?? undefined"
				class="relative mt-0.5 shrink-0"
			/>
			<div class="min-w-0 flex-1">
				<div class="flex items-center gap-2">
					<span class="truncate text-base font-medium text-ink-gray-8">{{ entry.owner_name }}</span>
					<time
						class="shrink-0 text-sm text-ink-gray-5"
						:datetime="entry.creation"
						:title="posted.format('D MMM YYYY, h:mm A')"
					>
						{{ posted.fromNow() }}
					</time>
					<Dropdown v-if="isAuthor && !editing" class="ml-auto" :options="actions" align="end">
						<button
							type="button"
							class="entry-menu rounded-4 p-0.5 text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-7"
							aria-label="Comment actions"
						>
							<span class="lucide-ellipsis size-4" aria-hidden="true" />
						</button>
					</Dropdown>
				</div>
				<CommentComposer
					v-if="editing"
					v-model="draft"
					:members="members"
					:loading="saving"
					editing
					class="mt-1"
					@submit="save"
					@cancel="editing = false"
				/>
				<!-- Notes are sanitized by Comment.validate, emails by the comments API and Frappe's inbox. -->
				<div
					v-else
					class="mt-0.5 text-base leading-relaxed text-pretty break-words text-ink-gray-7 [&_.mention]:rounded-4 [&_.mention]:bg-surface-gray-2 [&_.mention]:px-1 [&_.mention]:font-medium [&_.mention]:text-ink-gray-8 [&_p+p]:mt-2"
					v-html="entry.content"
				/>
				<p
					v-if="entry.kind === 'email'"
					class="mt-1.5 flex items-center gap-1.5 text-sm text-ink-gray-5"
				>
					<span
						:class="entry.received ? 'lucide-reply' : 'lucide-corner-down-right'"
						class="size-3.5"
						aria-hidden="true"
					/>
					{{ entry.received ? "Replied by email" : `Emailed to ${recipientNames}` }}
				</p>
			</div>
		</template>

		<template v-else>
			<span
				class="relative flex size-6 shrink-0 items-center justify-center rounded-full bg-surface-gray-2 text-ink-gray-5"
			>
				<span
					:class="entry.kind === 'change' ? 'lucide-circle-dot' : 'lucide-inbox'"
					class="size-3"
					aria-hidden="true"
				/>
			</span>
			<p class="min-w-0 flex-1 pt-0.5 text-sm text-ink-gray-5">
				<span class="font-medium text-ink-gray-7">{{ actor }}</span>
				{{ " " }}
				<template v-if="entry.kind === 'change'">
					moved this from {{ entry.old_value || "nothing" }} to
					<span class="text-ink-gray-7">{{ entry.new_value }}</span>
				</template>
				<template v-else>{{ createdLabel }}</template>
				·
				<time :datetime="entry.creation" :title="posted.format('D MMM YYYY, h:mm A')">{{
					posted.fromNow()
				}}</time>
			</p>
		</template>
	</li>
</template>

<style scoped>
.entry {
	transition:
		opacity 220ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 220ms cubic-bezier(0.23, 1, 0.32, 1);
}

/* A freshly posted note settles in rather than appearing. */
@starting-style {
	.entry {
		opacity: 0;
		transform: translateY(4px);
	}
}

@media (hover: hover) and (pointer: fine) {
	.entry-menu {
		opacity: 0;
		transition: opacity 120ms ease;
	}

	.entry:hover .entry-menu,
	.entry-menu:focus-visible,
	.entry-menu[aria-expanded="true"] {
		opacity: 1;
	}
}

@media (prefers-reduced-motion: reduce) {
	@starting-style {
		.entry {
			transform: none;
		}
	}
}
</style>
