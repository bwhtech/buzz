<script setup lang="ts">
import { Badge, Button, Dropdown, useList } from "frappe-ui"
import { computed } from "vue"
import LucidePlus from "~icons/lucide/plus"
import LucideX from "~icons/lucide/x"

import { topicIcon } from "@/utils/topicIcons"

const MAX_TOPICS = 5

const topics = defineModel<string[]>({ required: true })

const enabledTopics = useList<{ name: string }>({
	doctype: "Event Topic",
	fields: ["name"],
	filters: { enabled: 1 },
	orderBy: "name asc",
	limit: 100,
})

const isFull = computed(() => topics.value.length >= MAX_TOPICS)

const addOptions = computed(() =>
	(enabledTopics.data ?? [])
		.filter(({ name }) => !topics.value.includes(name))
		.map(({ name }) => ({ label: name, icon: topicIcon(name), onClick: () => add(name) })),
)

function add(name: string) {
	topics.value = [...topics.value, name]
}

function remove(name: string) {
	topics.value = topics.value.filter((topic) => topic !== name)
}
</script>

<template>
	<section class="space-y-3">
		<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">{{ __("Topics") }}</h2>
		<TransitionGroup tag="div" name="topic" class="flex flex-wrap items-center gap-1.5">
			<Badge v-for="name in topics" :key="name" size="lg" variant="subtle" :label="name">
				<template #prefix><component :is="topicIcon(name)" class="size-3.5" /></template>
				<template #suffix>
					<button
						class="relative -mr-1 grid size-4 place-items-center rounded-full text-ink-gray-5 transition-[background-color,color,transform] duration-150 ease-out before:absolute before:-inset-1 hover:bg-surface-gray-4 hover:text-ink-gray-8 focus-visible:outline-none focus-visible:focus-ring active:scale-90 motion-reduce:active:scale-100"
						:aria-label="__('Remove {0}', [name])"
						@click="remove(name)"
					>
						<LucideX class="size-3" />
					</button>
				</template>
			</Badge>
			<Dropdown v-if="!isFull && addOptions.length" key="add" :options="addOptions" align="start">
				<Button variant="ghost" size="xs" :icon-left="LucidePlus" :label="__('Add topic')" />
			</Dropdown>
		</TransitionGroup>
		<p v-if="isFull" class="text-p-sm text-ink-gray-5">
			{{ __("Limited to {0} items", [MAX_TOPICS]) }}
		</p>
	</section>
</template>

<style scoped>
.topic-enter-active {
	transition:
		opacity 150ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 150ms cubic-bezier(0.23, 1, 0.32, 1);
}

.topic-enter-from {
	opacity: 0;
	transform: scale(0.95);
}

@media (prefers-reduced-motion: reduce) {
	.topic-enter-from {
		transform: none;
	}
}
</style>
