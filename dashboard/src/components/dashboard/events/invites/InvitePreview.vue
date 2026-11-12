<script setup lang="ts">
import { refDebounced, useResizeObserver } from "@vueuse/core"
import { ErrorMessage, useCall } from "frappe-ui"
import { computed, ref } from "vue"

// The server renders the real invite email, event header included, so the preview is exact.
const props = defineProps<{ event: string; eventTitle: string; message: string }>()

const message = refDebounced(
	computed(() => props.message),
	300,
)
const preview = useCall<string, { event: string; message: string }>({
	url: "/api/v2/method/buzz.api.booking.invites.preview_invite",
	params: () => ({ event: props.event, message: message.value }),
	refetch: true,
})
const frame = ref<HTMLIFrameElement>()
const height = ref(560)

// A same-origin frame without scripts, so its height can be read to show the whole email.
// It refits when its width changes, since the email rewraps.
function fit() {
	// The body, not the document: the document is never shorter than the frame, so it can't shrink.
	const body = frame.value?.contentDocument?.body
	if (body) height.value = body.scrollHeight
}

useResizeObserver(frame, fit)
</script>

<template>
	<article
		class="overflow-hidden rounded-5 border border-outline-gray-1 bg-surface-elevation-1"
		aria-label="Invitation email preview"
	>
		<header class="truncate border-b border-outline-gray-1 px-4 py-2.5 text-p-sm text-ink-gray-6">
			Subject
			<span class="ml-2 font-medium text-ink-gray-9">You're invited to {{ eventTitle }}</span>
		</header>
		<ErrorMessage v-if="preview.error" class="p-4" :message="preview.error.message" />
		<!-- Links in the email are for the guest; clicking one here would only reload the frame. -->
		<iframe
			v-else-if="preview.data"
			ref="frame"
			:srcdoc="preview.data"
			sandbox="allow-same-origin"
			title="Invitation email"
			class="pointer-events-none block w-full"
			:style="{ height: `${height}px` }"
			@load="fit"
		/>
		<div v-else class="h-[560px] animate-pulse bg-surface-gray-1" />
	</article>
</template>
