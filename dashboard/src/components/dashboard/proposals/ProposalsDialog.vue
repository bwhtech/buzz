<script setup lang="ts">
import { Button, Dialog, call, toast } from "frappe-ui"
import { ref } from "vue"

const props = defineProps<{ event: string; closed: boolean }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ changed: [] }>()

const saving = ref(false)

// The server owns the state, so the toast reports what came back rather than what was asked for.
async function setClosed(closed: boolean) {
	saving.value = true
	try {
		const state: { proposals_closed: boolean } = await call(
			"buzz.api.proposals.set_proposal_state",
			{ event: props.event, closed },
		)
		if (state.proposals_closed === closed) {
			toast.success(closed ? "Proposals closed" : "Proposals open")
		} else {
			toast.warning("Proposals stay closed.")
		}
		emit("changed")
		isOpen.value = false
	} catch {
		toast.error(
			closed ? "Could not close proposals. Try again." : "Could not open proposals. Try again.",
		)
	} finally {
		saving.value = false
	}
}
</script>

<template>
	<Dialog v-model="isOpen" size="sm" :title="closed ? 'Open proposals' : 'Close proposals'">
		<div class="space-y-4">
			<p class="text-p-base text-ink-gray-6">
				{{
					closed
						? "The proposal page accepts new talks again."
						: "New talk proposals stop immediately. Proposals already in are unaffected."
				}}
			</p>

			<Button
				variant="solid"
				class="w-full"
				:theme="closed ? 'gray' : 'red'"
				:label="closed ? 'Open proposals' : 'Close proposals'"
				:loading="saving"
				@click="setClosed(!closed)"
			/>
		</div>
	</Dialog>
</template>
