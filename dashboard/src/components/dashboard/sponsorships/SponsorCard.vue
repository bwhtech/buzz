<script setup lang="ts">
import { Tooltip } from "frappe-ui"

import { tagColorClasses } from "@/components/common/tags/tagColors"
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

		<span class="flex min-w-0 flex-col gap-1.5 px-1 pb-1">
			<!-- Luma's colour dots; the drawer spells the tags out. The row keeps its height
			     when empty, so titles line up across cards. -->
			<span
				role="img"
				class="flex h-2 items-center gap-0.5 overflow-hidden"
				:class="!sponsor.tags.length && 'invisible'"
				:aria-hidden="!sponsor.tags.length || undefined"
				:aria-label="`Tags: ${sponsor.tags.map((tag) => tag.label).join(', ')}`"
			>
				<Tooltip v-for="tag in sponsor.tags" :key="tag.name" :text="tag.label">
					<span class="size-2 shrink-0 rounded-full" :class="tagColorClasses(tag.color).dot" />
				</Tooltip>
			</span>
			<span class="flex min-w-0 flex-col gap-0.5">
				<span class="truncate text-base font-medium text-ink-gray-8" :title="sponsor.company_name">
					{{ sponsor.company_name }}
				</span>
				<span class="truncate text-sm text-ink-gray-5" :title="sponsor.tier_title">
					{{ sponsor.tier_title }}
				</span>
			</span>
		</span>
	</button>
</template>
