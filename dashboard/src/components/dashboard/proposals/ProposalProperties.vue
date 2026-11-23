<script setup lang="ts">
import { Avatar } from "frappe-ui"

import DetailRow from "@/components/common/DetailRow.vue"
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
	<dl class="space-y-3 text-base">
		<DetailRow v-if="speakers.length" wrap label="Speakers" icon="lucide-users">
			<div class="space-y-1.5">
				<div
					v-for="speaker in speakers"
					:key="speaker.email"
					class="flex min-w-0 items-center gap-2"
				>
					<Avatar size="xs" :label="speakerName(speaker)" :theme="avatarTheme(speaker.email)" />
					<span class="shrink-0">{{ speakerName(speaker) }}</span>
					<span class="truncate text-sm text-ink-gray-5">{{ speaker.email }}</span>
				</div>
			</div>
		</DetailRow>
		<DetailRow
			v-for="field in fields"
			wrap
			:key="field.label"
			:label="field.label"
			:icon="field.icon"
		>
			{{ field.value }}
		</DetailRow>
	</dl>
</template>
