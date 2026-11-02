<script setup lang="ts">
import { BottomSheet, Button, toast } from "frappe-ui"
import { computed } from "vue"

import type { FrappeError } from "@/types"

import { dotColor } from "../scheduleColors"
import type { ScheduleTrack } from "../scheduleTypes"
import { useBuilder } from "../useScheduleBoard"
import { useMobile } from "./useScheduleMobile"

const builder = useBuilder()
const mobile = useMobile()

const open = computed(() => mobile.sheet.value?.type === "tracks")
const tracks = builder.tracks.tracks

const withErrorToast = (action: Promise<unknown>) =>
	action.catch((error: FrappeError) => toast.error(error.message || "Could not change the track"))

function rename(track: ScheduleTrack, event: Event) {
	const input = event.target as HTMLInputElement
	const title = input.value.trim()
	if (!title || title === track.title) input.value = track.title
	else withErrorToast(builder.renameTrack(track.name, title))
}

function remove(track: ScheduleTrack) {
	const message = `Delete ${track.title}? Its items on every day are deleted with it.`
	if (window.confirm(message)) withErrorToast(builder.removeTrack(track.name))
}
</script>

<template>
	<BottomSheet :open="open" @update:open="(value) => !value && mobile.closeSheet()">
		<div class="flex flex-col">
			<div class="px-5 pb-2 pt-2 text-xl font-semibold text-ink-gray-9">Tracks</div>
			<div class="flex flex-col px-5">
				<div
					v-for="(track, index) in tracks"
					:key="track.name"
					class="flex items-center gap-2 border-b border-outline-gray-1 py-2.5"
				>
					<span
						class="size-2 shrink-0 rounded-full"
						:style="{ background: dotColor(track.color) }"
						aria-hidden="true"
					/>
					<input
						:value="track.title"
						aria-label="Track title"
						class="min-w-0 flex-1 bg-transparent text-base text-ink-gray-9 outline-none"
						@change="rename(track, $event)"
						@keydown.enter="($event.target as HTMLInputElement).blur()"
					/>
					<Button
						variant="ghost"
						icon="lucide-arrow-up"
						label="Move up"
						:disabled="index === 0"
						@click="withErrorToast(builder.moveTrack(track.name, index - 1))"
					/>
					<Button
						variant="ghost"
						icon="lucide-arrow-down"
						label="Move down"
						:disabled="index === tracks.length - 1"
						@click="withErrorToast(builder.moveTrack(track.name, index + 1))"
					/>
					<Button
						variant="ghost"
						theme="red"
						icon="lucide-trash-2"
						label="Delete track"
						:disabled="tracks.length === 1"
						@click="remove(track)"
					/>
				</div>
			</div>
			<div class="flex gap-2 px-5 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-3.5">
				<Button
					class="flex-1"
					variant="subtle"
					size="lg"
					icon-left="lucide-plus"
					label="Add track"
					@click="mobile.addTrack"
				/>
				<Button class="flex-1" variant="solid" size="lg" label="Done" @click="mobile.closeSheet" />
			</div>
		</div>
	</BottomSheet>
</template>
