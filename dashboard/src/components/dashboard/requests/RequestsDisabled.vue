<script setup lang="ts">
import EmptyState from "@/components/common/EmptyState.vue"
import type { RequestType } from "@/types"

const props = defineProps<{ type: RequestType }>()

const COPY = {
	Approval: {
		icon: "lucide-user-check",
		title: "Approvals are off",
		description: "Pick Manual review or Review some tickets above to review registrations here.",
	},
	Waitlist: {
		icon: "lucide-list-ordered",
		title: "The waitlist is off",
		description: "Turn it on above to let people queue for sold-out tickets.",
	},
}
const copy = COPY[props.type]
</script>

<template>
	<EmptyState v-bind="copy" />
</template>
