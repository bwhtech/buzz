<script setup lang="ts">
import { Button, Dialog, call, toast } from "frappe-ui"
import { ref } from "vue"

const props = defineProps<{ event: string; closed: boolean }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ changed: [] }>()

const saving = ref(false)

// ponytail: there is no on/off flag — closure is derived from `registrations_close_at`,
// so closing writes "now" and opening clears the cutoff. An event that has already ended
// stays closed either way; give it a real flag if that needs to change.
async function setClosed(closed: boolean) {
	saving.value = true
	try {
		await call("frappe.client.set_value", {
			doctype: "Buzz Event",
			name: props.event,
			fieldname: "registrations_close_at",
			value: closed ? new Date().toISOString().slice(0, 19).replace("T", " ") : null,
		})
		toast.success(closed ? "Registrations closed" : "Registrations open")
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
