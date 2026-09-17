<script setup lang="ts">
import LogoPanel from "@/components/dashboard/sponsorships/LogoPanel.vue"
import type { EventSponsorItem } from "@/types"

defineProps<{ sponsor: EventSponsorItem }>()
defineEmits<{ open: [] }>()
</script>

<template>
	<button
		type="button"
		class="group flex min-w-0 flex-col gap-3 rounded-4 border border-outline-gray-2 p-2 text-left transition-[background-color,transform] duration-150 ease-out hover:bg-surface-gray-1 active:scale-[0.98] focus-visible:focus-ring motion-reduce:transform-none"
		@click="$emit('open')"
	>
		<!-- Logos stay grey until hovered, so a wall of brands reads calmly. Touch screens
		     cannot hover, so they get colour from the start. -->
		<LogoPanel
			class="transition-[filter] duration-200 ease-out [@media(hover:hover)]:grayscale group-hover:grayscale-0 group-focus-visible:grayscale-0"
			:src="sponsor.company_logo"
			:name="sponsor.company_name"
		/>

		<span class="flex min-w-0 items-baseline justify-between gap-2 px-1 pb-1">
			<span class="min-w-0 truncate text-base font-medium text-ink-gray-8">
				{{ sponsor.company_name }}
			</span>
			<span class="shrink-0 text-sm text-ink-gray-5">{{ sponsor.tier_title }}</span>
		</span>
	</button>
</template>
