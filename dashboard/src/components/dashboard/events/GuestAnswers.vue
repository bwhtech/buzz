<script setup lang="ts">
import CollapsibleCard from "@/components/common/CollapsibleCard.vue"
import type { GuestAnswer } from "@/types"

defineProps<{ answers: GuestAnswer[] }>()
</script>

<template>
	<CollapsibleCard
		icon="lucide-clipboard-list"
		title="Registration answers"
		:summary="`${answers.length} ${answers.length === 1 ? 'answer' : 'answers'}`"
	>
		<dl class="divide-y divide-outline-gray-1 px-4">
			<div v-for="answer in answers" :key="answer.label" class="space-y-1 py-3">
				<dt class="text-sm text-pretty text-ink-gray-5">{{ answer.label }}</dt>
				<dd class="text-base whitespace-pre-line [overflow-wrap:anywhere] text-ink-gray-8">
					{{ answer.value }}
				</dd>
			</div>
		</dl>
	</CollapsibleCard>
</template>
