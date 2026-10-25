<script setup lang="ts">
import { Avatar, Badge, Button, Dropdown, Tooltip, dayjsLocal } from "frappe-ui"
import { computed, ref } from "vue"

import { sessionUser } from "@/data/session"
import type { ActivityEntry, TeamMember } from "@/types"
import type { BadgeTheme } from "@/utils/badgeTheme"
import { trimTrailingEmptyParagraphs } from "@/utils/communicationText"

import ActivityEmail from "./ActivityEmail.vue"
import CommentComposer from "./CommentComposer.vue"

const props = defineProps<{
	entry: ActivityEntry
	members: TeamMember[]
	// Display names for email addresses, so recipients read as people.
	names: Record<string, string>
	createdLabel: string
	// Colours a tracked field's old and new value, such as a proposal's status.
	changeTheme?: (value: string) => BadgeTheme
	saving?: boolean
	fresh?: boolean
	folded?: boolean
	highlighted?: boolean
}>()

const emit = defineEmits<{ update: [content: string]; delete: [] }>()

const editing = ref(false)
const draft = ref("")

const posted = computed(() => dayjsLocal(props.entry.creation))
const exactTime = computed(() => posted.value.format("D MMM YYYY, h:mm A"))
const isEvent = computed(() => props.entry.kind === "change" || props.entry.kind === "created")
const isAuthor = computed(
	() => props.entry.kind === "comment" && props.entry.owner === sessionUser(),
)
const actor = computed(() => (props.entry.owner === "Guest" ? "Someone" : props.entry.owner_name))
const theme = (value: string | null) => (value && props.changeTheme?.(value)) || "gray"

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
	<li
		class="entry relative flex items-start gap-3"
		:data-entry="entry.name"
		:data-fresh="fresh || undefined"
		:data-highlighted="highlighted || undefined"
	>
		<!-- The rail lane: a ringed icon for events, an avatar for notes and emails. -->
		<div
			class="relative z-[1] flex w-7 shrink-0 justify-center"
			:class="entry.kind === 'email' && 'pt-2.5'"
		>
			<span
				v-if="isEvent"
				class="flex size-[22px] items-center justify-center rounded-full bg-surface-base text-ink-gray-5 ring-1 ring-outline-gray-2"
			>
				<span
					:class="entry.kind === 'change' ? 'lucide-circle-dot' : 'lucide-inbox'"
					class="size-3"
					aria-hidden="true"
				/>
			</span>
			<Avatar
				v-else
				size="md"
				:label="entry.owner_name"
				:image="entry.owner_image ?? undefined"
				class="ring-[3px] ring-[color:var(--surface-base)]"
			/>
		</div>

		<p
			v-if="isEvent"
			class="flex min-w-0 flex-1 flex-wrap items-center gap-x-1.5 gap-y-1 text-sm leading-[22px] text-ink-gray-5"
		>
			<span class="font-medium text-ink-gray-8">{{ actor }}</span>
			<template v-if="entry.kind === 'change'">
				<span>changed {{ entry.field }}</span>
				<span class="inline-flex items-center gap-1">
					<Badge
						v-if="entry.old_value"
						:theme="theme(entry.old_value)"
						variant="subtle"
						size="sm"
						:label="entry.old_value"
					/>
					<span v-if="entry.old_value" class="lucide-arrow-right size-3" aria-hidden="true" />
					<Badge
						:theme="theme(entry.new_value)"
						variant="subtle"
						size="sm"
						:label="entry.new_value || ''"
					/>
				</span>
			</template>
			<span v-else>{{ createdLabel }}</span>
			<span class="text-ink-gray-4" aria-hidden="true">·</span>
			<Tooltip :text="exactTime">
				<time :datetime="entry.creation">{{ posted.fromNow() }}</time>
			</Tooltip>
		</p>

		<ActivityEmail
			v-else-if="entry.kind === 'email'"
			:entry="entry"
			:names="names"
			:posted="posted.fromNow()"
			:exact-time="exactTime"
			:folded="folded"
		/>

		<div v-else class="flex min-w-0 flex-1 flex-col gap-1.5 py-0.5">
			<div class="flex items-center gap-2">
				<span class="truncate text-base font-semibold text-ink-gray-9">{{ entry.owner_name }}</span>
				<span class="inline-flex shrink-0 items-center gap-1 text-sm text-ink-gray-5">
					<span class="lucide-lock size-3" aria-hidden="true" />
					Internal note
				</span>
				<Tooltip :text="exactTime">
					<time class="ml-auto shrink-0 text-sm text-ink-gray-5" :datetime="entry.creation">
						{{ posted.fromNow() }}
					</time>
				</Tooltip>
				<Dropdown v-if="isAuthor && !editing" :options="actions" align="end">
					<Button
						class="entry-menu"
						variant="ghost"
						size="sm"
						icon="lucide-ellipsis"
						aria-label="Comment actions"
					/>
				</Dropdown>
			</div>
			<CommentComposer
				v-if="editing"
				v-model="draft"
				:members="members"
				:loading="saving"
				editing
				@submit="save"
				@cancel="editing = false"
			/>
			<!-- Sanitized by Comment.validate. -->
			<div
				v-else
				class="max-w-[68ch] text-base leading-[1.6] text-pretty break-words text-ink-gray-8 [&_.mention]:rounded-4 [&_.mention]:bg-surface-gray-2 [&_.mention]:px-1 [&_.mention]:font-medium [&_.mention]:text-ink-gray-9 [&_p+p]:mt-2"
				v-html="trimTrailingEmptyParagraphs(entry.content || '')"
			/>
		</div>
	</li>
</template>

<style scoped>
/* The rail: each entry draws from its marker to the next one's, past the 18px list gap,
   so the line stops at the last entry. */
.entry:not(:last-child)::before {
	content: "";
	position: absolute;
	top: 8px;
	bottom: -26px;
	left: 13.5px;
	width: 1px;
	background: var(--surface-gray-3);
}

.entry[data-fresh] {
	transition:
		opacity 220ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 220ms cubic-bezier(0.23, 1, 0.32, 1);
}

/* A freshly posted note settles in rather than appearing. */
@starting-style {
	.entry[data-fresh] {
		opacity: 0;
		transform: translateY(4px);
	}
}

/* A linked entry holds a tint long enough to be found, then lets it go. */
.entry[data-highlighted]::after {
	content: "";
	position: absolute;
	inset: -6px -8px;
	z-index: -1;
	border-radius: 10px;
	background: var(--surface-gray-2);
	opacity: 0;
	animation: highlight-fade 2400ms ease both;
}

.entry[data-highlighted] {
	isolation: isolate;
}

@keyframes highlight-fade {
	0%,
	50% {
		opacity: 1;
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
		.entry[data-fresh] {
			transform: none;
		}
	}
}
</style>
