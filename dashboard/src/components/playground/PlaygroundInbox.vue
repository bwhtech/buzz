<script setup lang="ts">
import { Dialog, dayjsLocal, useCall } from "frappe-ui"
import { computed, ref, watch } from "vue"

interface InboxEmail {
	name: string
	subject: string | null
	sender: string | null
	recipient: string | null
	creation: string
	message: string | null
	attachments: { name: string; file_name: string }[]
}

const open = defineModel<boolean>({ required: true })
const selectedName = ref<string>()

const inbox = useCall<InboxEmail[]>({
	url: "/api/v2/method/buzz.api.playground.get_inbox",
	immediate: false,
})
watch(open, (isOpen) => isOpen && inbox.reload())

const emails = computed(() => inbox.data ?? [])
const selected = computed(
	() => emails.value.find((email) => email.name === selectedName.value) ?? emails.value[0],
)
// Links leave the sandboxed frame for a new tab instead of navigating inside it.
const document = computed(() => `<base target="_blank">${selected.value?.message ?? ""}`)

function downloadUrl(file: string) {
	return `/api/method/buzz.api.playground.download_attachment?file=${encodeURIComponent(file)}`
}
</script>

<template>
	<Dialog v-model="open" :title="__('Inbox')" size="5xl">
		<p v-if="!emails.length" class="py-16 text-center text-base text-ink-gray-6">
			{{ __("Emails Buzz sends from this sandbox land here. Try booking a ticket.") }}
		</p>
		<div v-else class="flex h-[65vh] gap-4">
			<ul class="flex w-64 shrink-0 flex-col gap-0.5 overflow-y-auto">
				<li v-for="email in emails" :key="email.name">
					<button
						class="flex w-full flex-col gap-1 rounded px-3 py-2 text-left hover:bg-surface-gray-2"
						:class="{ 'bg-surface-gray-3': email.name === selected?.name }"
						@click="selectedName = email.name"
					>
						<span class="truncate text-sm-medium text-ink-gray-9">{{ email.subject }}</span>
						<span class="truncate text-sm text-ink-gray-6">{{ email.recipient }}</span>
					</button>
				</li>
			</ul>
			<div v-if="selected" class="flex min-w-0 flex-1 flex-col gap-3">
				<div class="flex flex-col gap-1">
					<h3 class="text-lg-semibold text-ink-gray-9">{{ selected.subject }}</h3>
					<p class="text-sm text-ink-gray-7">
						{{ __("From {0} to {1}", [selected.sender, selected.recipient]) }} ·
						{{ dayjsLocal(selected.creation).fromNow() }}
					</p>
					<div v-if="selected.attachments.length" class="flex flex-wrap gap-2 pt-1">
						<a
							v-for="attachment in selected.attachments"
							:key="attachment.name"
							:href="downloadUrl(attachment.name)"
							class="rounded border border-outline-gray-2 px-2 py-1 text-sm text-ink-gray-8 hover:bg-surface-gray-2"
						>
							{{ attachment.file_name }}
						</a>
					</div>
				</div>
				<iframe
					:srcdoc="document"
					sandbox="allow-popups allow-popups-to-escape-sandbox"
					class="w-full flex-1 rounded border border-outline-gray-2 bg-white"
				/>
			</div>
		</div>
	</Dialog>
</template>
