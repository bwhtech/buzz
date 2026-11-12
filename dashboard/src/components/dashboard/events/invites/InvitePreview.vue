<script setup lang="ts">
// Mirrors buzz/templates/emails/booking_invite.html, so the organizer sees what is sent.
defineProps<{ eventTitle: string; host: string; message: string }>()
</script>

<template>
	<article
		class="overflow-hidden rounded-5 border border-outline-gray-1 bg-surface-white text-ink-gray-8"
		aria-label="Invitation email preview"
	>
		<header class="truncate border-b border-outline-gray-1 px-4 py-2.5 text-p-sm text-ink-gray-6">
			Subject
			<span class="ml-2 font-medium text-ink-gray-9">You're invited to {{ eventTitle }}</span>
		</header>
		<div class="space-y-4 px-5 py-5 text-p-base leading-relaxed">
			<p class="text-xl font-semibold text-ink-gray-9">You're invited</p>
			<p>
				{{ host }} invited you to <strong class="text-ink-gray-9">{{ eventTitle }}</strong
				>. Your ticket is on the house.
			</p>
			<p v-if="message.trim()" class="whitespace-pre-line">{{ message }}</p>
			<span
				class="inline-block rounded-3 bg-surface-gray-9 px-3 py-1.5 text-p-sm font-medium text-ink-white"
			>
				Accept invitation
			</span>
		</div>
	</article>
</template>
