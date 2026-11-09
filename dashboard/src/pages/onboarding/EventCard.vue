<script setup lang="ts">
import { bannerPattern } from "@public/js/event_banner"
import { Avatar } from "frappe-ui"
import { computed } from "vue"
import LucideMapPin from "~icons/lucide/map-pin"
import LucideVideo from "~icons/lucide/video"

import { effectiveChoice, flow, fullName, profile } from "./useOnboarding"

const event = flow.event
const host = computed(() =>
	effectiveChoice.value === "community" && flow.community.team_name
		? { name: flow.community.team_name, image: flow.community.logo }
		: { name: fullName.value, image: profile.user_image },
)
const date = computed(() =>
	event.start_date ? new Date(`${event.start_date}T${event.start_time || "00:00"}`) : null,
)
const month = computed(() => date.value?.toLocaleString(undefined, { month: "short" }) ?? "—")
const day = computed(() => date.value?.getDate() ?? "")
const when = computed(
	() =>
		date.value?.toLocaleString(undefined, {
			weekday: "long",
			hour: "numeric",
			minute: "2-digit",
		}) ?? __("Pick a date and time"),
)
const online = computed(() => event.medium === "Online")
</script>

<template>
	<article
		class="w-full max-w-xs overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-elevation-1 shadow-sm"
	>
		<div
			class="aspect-[16/9]"
			:style="{ backgroundImage: bannerPattern(event.title || __('Untitled')) }"
		/>
		<div class="flex flex-col gap-3 p-4">
			<div class="flex items-start gap-3">
				<div
					class="flex w-10 shrink-0 flex-col overflow-hidden rounded-md border border-outline-gray-2 text-center"
				>
					<span class="bg-surface-gray-2 text-2xs-medium uppercase text-ink-gray-6">{{
						month
					}}</span>
					<span class="py-0.5 text-base-semibold text-ink-gray-9 tabular-nums">{{ day }}</span>
				</div>
				<div class="flex min-w-0 flex-col gap-0.5">
					<p class="truncate text-base-semibold text-ink-gray-9">
						{{ event.title || __("Untitled event") }}
					</p>
					<p class="text-sm text-ink-gray-5">{{ when }}</p>
				</div>
			</div>
			<p class="flex items-center gap-1.5 text-sm text-ink-gray-6">
				<LucideVideo v-if="online" class="size-3.5" />
				<LucideMapPin v-else class="size-3.5" />
				<span class="truncate">{{
					online ? __("Online") : event.venue_name || __("Venue to be added")
				}}</span>
			</p>
			<div class="flex items-center gap-2 border-t border-outline-gray-1 pt-3">
				<Avatar size="xs" :image="host.image || undefined" :label="host.name || '?'" />
				<span class="truncate text-sm text-ink-gray-6">
					{{ __("Hosted by {0}", [host.name]) }}
				</span>
			</div>
		</div>
	</article>
</template>
