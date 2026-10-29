<script setup lang="ts">
import { Badge, Button, dayjs } from "frappe-ui"

import { dotColor } from "./scheduleColors"
import { clock, timeRange } from "./scheduleLayout"
import { useDayLayout } from "./useDayLayout"

const { builder, board, roomIndex } = useDayLayout()

function itemsOf(date: string) {
	return builder
		.dayItems(date)
		.toSorted(
			(a, b) =>
				a.start - b.start ||
				(roomIndex.value[a.room ?? ""] ?? -1) - (roomIndex.value[b.room ?? ""] ?? -1),
		)
}

function span(date: string) {
	const list = itemsOf(date)
	if (!list.length) return "Empty"
	return `${clock(list[0].start)} – ${clock(Math.max(...list.map((item) => item.start + item.duration)))}`
}

function open(date: string) {
	builder.activeDate.value = date
	board.view.value = "calendar"
}
</script>

<template>
	<div class="h-full overflow-auto px-5 py-4">
		<div class="flex items-start gap-3">
			<div
				v-for="day in builder.days.value"
				:key="day.date"
				class="box-border flex w-[300px] shrink-0 flex-col gap-1.5 rounded-6 border p-2 transition-colors"
				:class="
					board.dropDay.value === day.date
						? 'border-dashed border-outline-blue-3 bg-surface-blue-1'
						: 'border-outline-gray-1 bg-surface-gray-1'
				"
				@dragover="board.dayOver(day.date)($event)"
				@drop="board.dayDrop(day.date)($event)"
				@dragleave="board.dayLeave($event)"
			>
				<div class="flex items-center gap-2 pb-1.5 pl-1.5 pr-1 pt-1">
					<div class="min-w-0 flex-1">
						<div class="text-p-base font-semibold text-ink-gray-9">{{ day.label }}</div>
						<div class="text-p-xs text-ink-gray-5">
							{{ dayjs(day.date).format("ddd D MMM") }} · {{ span(day.date) }}
						</div>
					</div>
					<Badge :label="String(itemsOf(day.date).length)" theme="gray" />
					<Button
						variant="ghost"
						size="sm"
						icon="lucide-arrow-up-right"
						label="Open in calendar"
						@click="open(day.date)"
					/>
				</div>
				<div
					v-for="item in itemsOf(day.date)"
					:key="item.key"
					draggable="true"
					class="flex cursor-grab flex-col gap-1 rounded-4 border bg-surface-base px-2.5 py-2"
					:class="[
						builder.conflicts(builder.dayItems(day.date))[item.key]
							? 'border-outline-red-3'
							: 'border-outline-gray-2',
						board.selectedKey.value === item.key && 'ring-2 ring-outline-gray-9',
						board.dragKey.value === item.key && 'opacity-40',
					]"
					@click="((builder.activeDate.value = day.date), board.select(item.key))"
					@dragstart="
						board.startDrag(
							{
								kind: 'item',
								id: item.key,
								duration: item.duration,
								span: !item.room,
								grabX: 0,
								grabY: 0,
							},
							$event,
						)
					"
					@dragend="board.endDrag"
				>
					<div class="flex items-center gap-1.5 text-p-xs tabular-nums text-ink-gray-5">
						<span
							class="size-2 shrink-0 rounded-full"
							:style="{ background: dotColor(builder.resolve(item).type?.color) }"
						/>
						<span class="flex-1">{{ timeRange(item) }}</span>
						<span class="whitespace-nowrap">{{ builder.rooms.titleOf(item.room) }}</span>
					</div>
					<div class="text-p-sm font-semibold leading-snug text-ink-gray-9">
						{{ builder.resolve(item).title }}
					</div>
				</div>
				<div
					v-if="!itemsOf(day.date).length"
					class="px-2 py-6 text-center text-p-xs text-ink-gray-5"
				>
					Drop talks or blocks here
				</div>
			</div>
			<div class="w-[200px] shrink-0 pt-1">
				<Button variant="ghost" iconLeft="lucide-plus" label="Add day" @click="builder.addDay" />
			</div>
		</div>
	</div>
</template>
