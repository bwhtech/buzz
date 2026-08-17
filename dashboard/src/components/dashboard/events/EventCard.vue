<script setup lang="ts">
import type { MyEvent } from "@/types";
import { bannerPattern } from "@/utils/eventBanner";
import { Avatar } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{ event: MyEvent }>();

// Times arrive as a serialized timedelta ("9:00:00"), so the hour needs padding.
const startTime = computed((): string => {
	if (!props.event.start_time) return "";
	const [hour, minute] = props.event.start_time.split(":");
	return `${hour.padStart(2, "0")}:${minute}`;
});

const banner = computed(() => ({ backgroundImage: bannerPattern(props.event.name) }));

// Only a host can fix a missing venue; for everyone else it is news, not a warning.
const venue = computed(() => {
	if (props.event.venue) return { label: props.event.venue, icon: "lucide-map-pin", tone: "" };
	if (props.event.is_host)
		return {
			label: "Location missing",
			icon: "lucide-triangle-alert",
			tone: "text-ink-amber-6",
		};
	return { label: "Venue to be announced", icon: "lucide-map-pin-off", tone: "" };
});
</script>

<template>
	<!-- TODO: some sort of action on click of this card -->
	<article
		class="flex gap-4 border border-outline-gray-2 hover:border-outline-gray-3 rounded-2xl p-3"
	>
		<!-- The pattern also backs the image, so the slot is never blank while it loads. -->
		<img
			v-if="event.banner_image"
			class="h-28 w-28 rounded object-cover object-top"
			:src="event.banner_image"
			:style="banner"
			loading="lazy"
			alt=""
		/>
		<div v-else class="h-28 w-28 rounded" :style="banner" />

		<div class="flex-1 py-1 flex flex-col justify-between">
			<div class="flex-1 space-y-2">
				<p v-if="startTime" class="text-base tabular-nums text-ink-gray-5">
					{{ startTime }}
				</p>

				<h3 class="font-semibold text-lg text-ink-gray-8">{{ event.title }}</h3>
				<p v-if="event.team_name" class="flex items-center gap-2 text-sm text-ink-gray-6">
					<Avatar
						:image="event.team_logo || undefined"
						:label="event.team_name"
						size="xs"
					/>
					By {{ event.team_name }}
				</p>
			</div>

			<p class="mt-2 flex items-center gap-2 text-base text-ink-gray-5">
				<span
					class="size-4 shrink-0"
					:class="[venue.icon, venue.tone]"
					aria-hidden="true"
				/>
				{{ venue.label }}
			</p>
		</div>
	</article>
</template>
