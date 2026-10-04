<script setup lang="ts">
import { Button, Dialog, call, toast } from "frappe-ui"
import { ref } from "vue"

const props = defineProps<{ event: string; closed: boolean }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ changed: [] }>()

const saving = ref(false)

// The server owns the state: an event that has already ended stays closed however this
// call is answered, so the toast reports what came back rather than what was asked for.
async function setClosed(closed: boolean) {
	saving.value = true
	try {
		const state: { registrations_closed: boolean } = await call(
			"buzz.api.events.set_registration_state",
			{ event: props.event, closed },
		)
		if (state.registrations_closed === closed) {
			toast.success(closed ? "Registrations closed" : "Registrations open")
		} else {
			toast.warning("Registrations stay closed: the event has ended.")
		}
		emit("changed")
		isOpen.value = false
	} catch {
		toast.error(
			closed
				? "Could not close registrations. Try again."
				: "Could not open registrations. Try again.",
		)
	} finally {
		saving.value = false
	}
}
</script>

<template>
	<Dialog v-model="isOpen" size="sm" :title="closed ? 'Open registrations' : 'Close registrations'">
		<div class="space-y-4">
			<p class="text-p-base text-ink-gray-6">
				{{
					closed
						? "The registration page accepts new registrations again."
						: "New registrations stop immediately. Existing registrations are unaffected."
				}}
			</p>

			<Button
				variant="solid"
				class="w-full"
				:theme="closed ? 'gray' : 'red'"
				:label="closed ? 'Open registrations' : 'Close registrations'"
				:loading="saving"
				@click="setClosed(!closed)"
			/>
		</div>
	</Dialog>
</template>
