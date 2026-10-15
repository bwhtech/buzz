<script setup lang="ts">
import { Avatar, Dropdown, dayjsLocal } from "frappe-ui"
import { computed, ref } from "vue"

import CommentEditor from "@/components/dashboard/comments/CommentEditor.vue"
import { sessionUser } from "@/data/session"
import type { DocumentComment, TeamMember } from "@/types"

const props = defineProps<{ comment: DocumentComment; members: TeamMember[]; saving?: boolean }>()

const emit = defineEmits<{ update: [content: string]; delete: [] }>()

const editing = ref(false)
const draft = ref("")

const isAuthor = computed(() => props.comment.owner === sessionUser())
const postedAt = computed(() => dayjsLocal(props.comment.creation))

const actions = [
	{ label: "Edit", icon: "lucide-pencil", onClick: startEditing },
	{ label: "Delete", icon: "lucide-trash-2", theme: "red" as const, onClick: () => emit("delete") },
]

function startEditing() {
	draft.value = props.comment.content
	editing.value = true
}

function save(content: string) {
	emit("update", content)
	editing.value = false
}
</script>

<template>
	<li class="flex gap-3">
		<Avatar size="md" :label="comment.owner_name" :image="comment.owner_image ?? undefined" />
		<div class="min-w-0 flex-1 space-y-1">
			<div class="flex items-center gap-2">
				<span class="truncate text-base font-medium text-ink-gray-8">{{ comment.owner_name }}</span>
				<time
					class="text-sm text-ink-gray-5"
					:datetime="comment.creation"
					:title="postedAt.format('D MMM YYYY, h:mm A')"
				>
					{{ postedAt.fromNow() }}
				</time>
				<Dropdown v-if="isAuthor && !editing" class="ml-auto" :options="actions">
					<button
						type="button"
						class="rounded-4 p-1 text-ink-gray-5 hover:bg-surface-gray-2"
						aria-label="Comment actions"
					>
						<span class="lucide-ellipsis size-4" aria-hidden="true" />
					</button>
				</Dropdown>
			</div>
			<CommentEditor
				v-if="editing"
				v-model="draft"
				:members="members"
				:loading="saving"
				submit-label="Save"
				@submit="save"
				@cancel="editing = false"
			/>
			<!-- Comment content is sanitized by Frappe's Comment.validate. -->
			<div
				v-else
				class="prose prose-sm max-w-none text-base text-ink-gray-7 [&_.mention]:font-medium [&_.mention]:text-ink-gray-9"
				v-html="comment.content"
			/>
		</div>
	</li>
</template>
