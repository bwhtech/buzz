<script setup lang="ts">
// The footer for each step. On a phone the hint sits above full-width buttons.
import { Button, ErrorMessage } from "frappe-ui"
import { computed } from "vue"

import { guestCount } from "./invites"
import type { InviteFlow } from "./useInviteFlow"

const props = defineProps<{ flow: InviteFlow }>()
const emit = defineEmits<{ addDirectly: [] }>()

const count = computed(() => props.flow.selection.selected.value.length)
const warning = computed(() => props.flow.attempted.value && props.flow.missingCount.value > 0)
const hint = computed(
	() =>
		({
			pick: count.value
				? `${guestCount(count.value)} selected`
				: "Add emails, or pick guests from a past event.",
			review: warning.value
				? `Add a first name for ${guestCount(props.flow.missingCount.value)} to add them directly.`
				: "Add directly books tickets now. Invites let guests accept by email.",
			message: "Each guest gets their own link to accept.",
		})[props.flow.stage.value],
)
</script>

<template>
	<footer
		class="flex gap-3 border-t border-outline-gray-1 px-4 py-3 max-md:flex-col max-md:pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-5 md:items-center"
	>
		<ErrorMessage v-if="flow.error.value" class="min-w-0 flex-1" :message="flow.error.value" />
		<!-- A fixed height on phones, so a wrapping hint never moves the buttons under a thumb. -->
		<div v-else class="flex min-w-0 flex-1 items-center gap-2 max-md:min-h-10">
			<p
				class="min-w-0 text-p-sm"
				:class="warning && flow.stage.value === 'review' ? 'text-ink-amber-7' : 'text-ink-gray-5'"
			>
				{{ hint }}
			</p>
			<Button
				v-if="flow.stage.value === 'pick' && count"
				variant="ghost"
				size="sm"
				label="Clear"
				@click="flow.selection.remove([...flow.selection.selected.value])"
			/>
		</div>
		<div class="flex gap-2 max-md:[&>*]:flex-1">
			<Button
				v-if="flow.stage.value === 'pick'"
				variant="solid"
				icon-right="lucide-arrow-right"
				label="Next"
				:disabled="!count"
				@click="flow.go('review')"
			/>
			<template v-else-if="flow.stage.value === 'review'">
				<Button
					variant="outline"
					label="Add directly"
					:loading="flow.busy.value"
					@click="emit('addDirectly')"
				/>
				<Button
					variant="solid"
					icon-right="lucide-arrow-right"
					label="Write invite"
					:disabled="flow.busy.value"
					@click="flow.go('message')"
				/>
			</template>
			<Button
				v-else
				variant="solid"
				icon-left="lucide-send"
				:label="`Send ${guestCount(count)}`"
				:loading="flow.busy.value"
				@click="flow.send"
			/>
		</div>
	</footer>
</template>
