<template>
	<div v-if="cancellationRequest" class="mb-6">
		<div class="bg-surface-blue-1 border border-outline-blue-1 rounded-lg p-4">
			<div class="flex items-center">
				<LucideInfo class="w-5 h-5 text-ink-blue-2 mr-3" />
				<div>
					<h3 class="text-ink-blue-3 font-semibold">
						{{ __("Cancellation Requested") }}
					</h3>
					<p class="text-ink-blue-2">
						<span v-if="cancellationRequest.cancel_full_booking">
							{{ __("Full booking cancellation has been requested.") }}
						</span>
						<span v-else>
							{{
								__("Partial cancellation has been requested for selected tickets.")
							}}
						</span>
						{{ __("Request submitted on") }}
						{{ formatDate(cancellationRequest.creation) }}.
					</p>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import LucideInfo from "~icons/lucide/info";

defineProps<{
	cancellationRequest?: Record<string, any> | null;
}>();

const formatDate = (dateString: string) => {
	return new Date(dateString).toLocaleDateString();
};
</script>
