<script setup lang="ts">
import { Avatar, Button, dialog, toast } from "frappe-ui"
import { ref } from "vue"

import AddCoHostDialog from "@/components/dashboard/events/AddCoHostDialog.vue"
import { useRemoveCoHost } from "@/data/events"
import type { EventHostRef } from "@/types"

const props = defineProps<{
	event: string
	primaryHost: EventHostRef | null
	coHosts: EventHostRef[]
}>()
const emit = defineEmits<{ changed: [] }>()

const adding = ref(false)
const removeCoHost = useRemoveCoHost()

function confirmRemove(host: EventHostRef) {
	dialog.confirm({
		title: __("Remove Co-host"),
		message: __("{0} will no longer be listed as a host of this event.", [host.label]),
		theme: "red",
		confirmLabel: __("Remove"),
		onConfirm: async () => {
			await removeCoHost.submit({ event: props.event, host: host.host })
			// useCall settles either way, so the failure has to be rethrown to reach the dialog.
			if (removeCoHost.error) throw removeCoHost.error
			emit("changed")
			toast.success(__("{0} was removed as a co-host.", [host.label]))
		},
	})
}
</script>

<template>
	<section class="space-y-3">
		<div class="flex items-center justify-between">
			<h2 class="text-sm font-medium uppercase tracking-wide text-ink-gray-5">Hosted by</h2>
			<Button :label="__('Add Co-host')" @click="adding = true" />
		</div>

		<TransitionGroup tag="ul" name="host" class="relative space-y-2">
			<li key="primary" v-if="primaryHost" class="flex items-center gap-3">
				<Avatar
					shape="square"
					size="lg"
					:image="primaryHost.logo ?? undefined"
					:label="primaryHost.label"
				/>
				<span class="truncate text-base text-ink-gray-8">{{ primaryHost.label }}</span>
			</li>

			<li v-for="host in coHosts" :key="host.host" class="flex items-center justify-between gap-3">
				<div class="flex min-w-0 items-center gap-3">
					<Avatar shape="square" size="lg" :image="host.logo ?? undefined" :label="host.label" />
					<span class="truncate text-base text-ink-gray-8">{{ host.label }}</span>
				</div>

				<Button
					variant="ghost"
					icon="lucide-x"
					:aria-label="__('Remove {0}', [host.label])"
					@click="confirmRemove(host)"
				/>
			</li>
		</TransitionGroup>

		<AddCoHostDialog v-model="adding" :event="event" @added="emit('changed')" />
	</section>
</template>

<style scoped>
.host-enter-active {
	transition:
		opacity 200ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}

.host-enter-from {
	opacity: 0;
	transform: translateY(0.5rem);
}

/* The leaving row is taken out of flow so the rows below start closing the gap
   straight away rather than waiting for the fade to finish. */
.host-leave-active {
	position: absolute;
	inset-inline: 0;
	transition:
		opacity 150ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 150ms cubic-bezier(0.23, 1, 0.32, 1);
}

.host-leave-to {
	opacity: 0;
	transform: translateX(0.5rem);
}

.host-move {
	transition: transform 250ms cubic-bezier(0.23, 1, 0.32, 1);
}

@media (prefers-reduced-motion: reduce) {
	.host-enter-from,
	.host-leave-to {
		transform: none;
	}

	.host-move {
		transition: none;
	}
}
</style>
