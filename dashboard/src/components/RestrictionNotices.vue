<template>
	<div>
		<!-- Single consolidated restriction notice -->
		<div v-if="hasRestrictions" class="mb-4">
			<div class="bg-surface-amber-1 border border-outline-amber-1 rounded-lg p-4">
				<div class="flex items-start">
					<LucideTriangleAlert
						class="w-5 h-5 text-ink-amber-5 mr-3 mt-0.5 flex-shrink-0"
					/>
					<div>
						<p class="text-ink-amber-6 text-sm-medium mb-2">
							{{
								__(
									"Some options are no longer available as the event is approaching:"
								)
							}}
						</p>
						<ul class="text-ink-amber-6 text-sm space-y-1 list-disc list-inside">
							<li v-if="!canRequestCancellation && !cancellationRequest">
								{{ __("Ticket cancellation requests") }}
							</li>
							<li v-if="!canTransferTickets">{{ __("Ticket transfers") }}</li>
							<li v-if="!canChangeAddOns">{{ __("Add-on preference changes") }}</li>
						</ul>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import LucideTriangleAlert from "~icons/lucide/triangle-alert";

const props = defineProps({
	canRequestCancellation: {
		type: Boolean,
		default: false,
	},
	canTransferTickets: {
		type: Boolean,
		default: false,
	},
	canChangeAddOns: {
		type: Boolean,
		default: false,
	},
	cancellationRequest: {
		type: Object,
		default: null,
	},
});

// Computed property to check if any restrictions exist
const hasRestrictions = computed(() => {
	return (
		(!props.canRequestCancellation && !props.cancellationRequest) ||
		!props.canTransferTickets ||
		!props.canChangeAddOns
	);
});
</script>
