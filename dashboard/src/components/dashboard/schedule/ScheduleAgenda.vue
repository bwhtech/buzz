<script setup lang="ts">
import { Button, FormControl } from "frappe-ui"
import { computed } from "vue"

import { dotColor } from "./scheduleColors"
import { clock, speakerLine, timeRange } from "./scheduleLayout"
import { useDayLayout } from "./useDayLayout"

const { builder, board, dayItems, roomIndex, conflicts } = useDayLayout()

const groups = computed(() => {
	const sorted = dayItems.value.toSorted(
		(a, b) =>
			a.start - b.start ||
			(roomIndex.value[a.room ?? ""] ?? -1) - (roomIndex.value[b.room ?? ""] ?? -1),
	)
	const starts = [...new Set(sorted.map((item) => item.start))]
	return starts.map((start) => ({ start, rows: sorted.filter((item) => item.start === start) }))
})
const roomOptions = computed(() => [
	{ label: "All rooms", value: "all" },
	...builder.rooms.rooms.value.map((room) => ({ label: room.title, value: room.name })),
])
const dayOptions = computed(() =>
	builder.days.value.map((day) => ({ label: day.label, value: day.date })),
)

function meta(item: (typeof dayItems.value)[number]) {
	const speakers = speakerLine(builder.resolve(item).speakers)
	return [timeRange(item), `${item.duration} min`, speakers].filter(Boolean).join(" · ")
}
</script>

<template>
	<div class="h-full overflow-auto">
		<div class="mx-auto max-w-[900px] px-6 pb-24 pt-3">
			<div v-if="!groups.length" class="flex flex-col items-center gap-1.5 py-[72px] text-center">
				<div class="text-[15px] font-semibold text-ink-gray-9">
					Nothing on {{ builder.activeDay.value?.label }} yet
				</div>
				<div class="text-p-sm text-ink-gray-5">
					Drag talks from the library, or switch to Calendar and click an empty slot
				</div>
			</div>
			<div
				v-for="group in groups"
				:key="group.start"
				class="flex gap-4 border-b border-outline-gray-1 py-3"
			>
				<div class="w-[88px] shrink-0 pt-2">
					<div class="text-p-base font-semibold tabular-nums text-ink-gray-9">
						{{ clock(group.start) }}
					</div>
					<div class="text-p-xs text-ink-gray-5">
						{{ group.rows.length > 1 ? `${group.rows.length} in parallel` : "" }}
					</div>
				</div>
				<div class="flex min-w-0 flex-1 flex-col gap-0.5">
					<div
						v-for="item in group.rows"
						:key="item.key"
						draggable="true"
						class="flex cursor-pointer items-center gap-3 rounded-5 border py-1.5 pl-2.5 pr-2 hover:bg-surface-gray-2"
						:class="[
							conflicts[item.key] ? 'border-outline-red-2' : 'border-transparent',
							board.selectedKey.value === item.key && 'bg-surface-gray-2',
							board.dragKey.value === item.key && 'opacity-40',
						]"
						@click="board.select(item.key)"
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
						<span
							class="size-2 shrink-0 rounded-full"
							:style="{ background: dotColor(builder.resolve(item).type?.color) }"
						/>
						<div class="min-w-0 flex-1">
							<div class="flex items-center gap-1.5">
								<div class="truncate text-p-base font-semibold text-ink-gray-9">
									{{ builder.resolve(item).title }}
								</div>
								<span
									v-if="conflicts[item.key]"
									class="lucide-triangle-alert size-3.5 shrink-0 text-ink-red-5"
									role="img"
									:aria-label="conflicts[item.key]"
								/>
							</div>
							<div class="truncate text-p-xs tabular-nums text-ink-gray-5">{{ meta(item) }}</div>
						</div>
						<div class="w-[150px] shrink-0" @click.stop>
							<FormControl
								type="select"
								:options="roomOptions"
								:model-value="item.room ?? 'all'"
								@update:model-value="
									(value: string) =>
										builder.update(
											item.key,
											{ room: value === 'all' ? null : value },
											`Moved to ${builder.rooms.titleOf(value === 'all' ? null : value)}`,
										)
								"
							/>
						</div>
						<div class="w-24 shrink-0" @click.stop>
							<FormControl
								type="select"
								:options="dayOptions"
								:model-value="item.date"
								@update:model-value="
									(value: string) => builder.place({ kind: 'item', id: item.key }, value)
								"
							/>
						</div>
						<Button
							variant="ghost"
							icon="lucide-x"
							label="Remove from schedule"
							@click.stop="builder.remove(item.key)"
						/>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
