<script setup lang="ts">
import { Button, Tooltip } from "frappe-ui"

import type { EmailAttachmentChoice } from "@/data/comments"

const attached = defineModel<EmailAttachmentChoice[]>({ required: true })

const remove = (choice: EmailAttachmentChoice) =>
	(attached.value = attached.value.filter((existing) => existing.key !== choice.key))
</script>

<template>
	<!-- Every file goes out with this one email; any can be dropped before it is sent. -->
	<div v-if="attached.length" class="mx-3 mt-1 rounded-4 border border-outline-gray-2">
		<p class="border-b border-outline-gray-1 px-2.5 py-1.5 text-xs text-ink-gray-5">
			{{ attached.length }} {{ attached.length === 1 ? "attachment" : "attachments" }}
		</p>
		<ul class="max-h-40 overflow-y-auto py-1" aria-label="Attachments">
			<li
				v-for="choice in attached"
				:key="choice.key"
				class="attachment flex items-center gap-2.5 px-2.5 py-1"
			>
				<span
					class="flex size-7 shrink-0 items-center justify-center rounded-3 bg-surface-gray-2 text-ink-gray-6"
				>
					<span :class="choice.icon" class="size-3.5" aria-hidden="true" />
				</span>
				<span class="min-w-0 flex-1">
					<span class="block truncate text-sm text-ink-gray-8">{{ choice.fileName }}</span>
					<span
						v-if="choice.label !== choice.fileName"
						class="block truncate text-xs text-ink-gray-5"
					>
						{{ choice.label }}
					</span>
				</span>
				<Tooltip text="Remove">
					<Button
						variant="ghost"
						size="sm"
						icon="lucide-x"
						:aria-label="`Remove ${choice.fileName}`"
						@click="remove(choice)"
					/>
				</Tooltip>
			</li>
		</ul>
	</div>
</template>

<style scoped>
.attachment {
	transition:
		opacity 160ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 160ms cubic-bezier(0.23, 1, 0.32, 1);
}

@starting-style {
	.attachment {
		opacity: 0;
		transform: translateY(-2px);
	}
}

@media (prefers-reduced-motion: reduce) {
	@starting-style {
		.attachment {
			transform: none;
		}
	}
}
</style>
