<script setup lang="ts">
import { Avatar } from "frappe-ui"

import type { ProposalSpeaker } from "@/types"
import { speakerName } from "@/utils/speakerByline"

defineProps<{
	speakers: ProposalSpeaker[]
	fields: { label: string; value: string; icon: string }[]
}>()

// One theme per speaker, stable across renders so a face keeps its colour.
const AVATAR_THEMES = ["blue", "green", "amber", "red", "violet"] as const
const avatarTheme = (email: string) => {
	const seed = [...email].reduce((total, character) => total + character.charCodeAt(0), 0)
	return AVATAR_THEMES[seed % AVATAR_THEMES.length]
}
</script>

<template>
	<dl class="space-y-0.5">
		<div v-if="speakers.length" class="flex items-start gap-3 py-1.5">
			<dt class="flex w-32 shrink-0 items-center gap-2 text-base text-ink-gray-5">
				<span class="lucide-users size-4" aria-hidden="true" />Speakers
			</dt>
			<dd class="min-w-0 flex-1 space-y-1.5">
				<div
					v-for="speaker in speakers"
					:key="speaker.email"
					class="flex min-w-0 items-center gap-2"
				>
					<Avatar size="xs" :label="speakerName(speaker)" :theme="avatarTheme(speaker.email)" />
					<span class="shrink-0 text-base text-ink-gray-8">{{ speakerName(speaker) }}</span>
					<span class="truncate text-sm text-ink-gray-5">{{ speaker.email }}</span>
				</div>
			</dd>
		</div>
		<div v-for="field in fields" :key="field.label" class="flex items-start gap-3 py-1.5">
			<dt class="flex w-32 shrink-0 items-center gap-2 text-base text-ink-gray-5">
				<span :class="field.icon" class="size-4 shrink-0" aria-hidden="true" />
				<span class="truncate">{{ field.label }}</span>
			</dt>
			<dd class="min-w-0 flex-1 text-base break-words text-ink-gray-8">{{ field.value }}</dd>
		</div>
	</dl>
</template>
