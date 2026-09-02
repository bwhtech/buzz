<script setup lang="ts">
import { Button, Dialog, FormControl } from "frappe-ui"
import { computed, ref, watch } from "vue"

import type { ProposalSpeaker } from "@/types"

const props = defineProps<{ speakers: ProposalSpeaker[]; saving?: boolean }>()

const emit = defineEmits<{ add: [speaker: ProposalSpeaker] }>()

const open = defineModel<boolean>("open", { required: true })

const form = ref({ first_name: "", last_name: "", email: "" })

// Latched on submit: the roster gains this very speaker while the dialog is still up,
// and without the latch the warning fires on the add that just succeeded.
const submitted = ref(false)

// Guest-entered speaker emails keep their casing, so the match is case-insensitive.
const alreadyListed = computed(
	() =>
		!submitted.value &&
		props.speakers.some(
			(speaker) => speaker.email.toLowerCase() === form.value.email.trim().toLowerCase(),
		),
)

const canSubmit = computed(
	() => Boolean(form.value.first_name.trim() && form.value.email.trim()) && !alreadyListed.value,
)

watch(open, (showing) => {
	if (!showing) return
	form.value = { first_name: "", last_name: "", email: "" }
	submitted.value = false
})

// A rejected add leaves the dialog up, so the latch has to come off with the spinner.
watch(
	() => props.saving,
	(now, before) => {
		if (before && !now) submitted.value = false
	},
)

function submit() {
	if (!canSubmit.value) return
	submitted.value = true
	emit("add", {
		first_name: form.value.first_name.trim(),
		last_name: form.value.last_name.trim() || null,
		email: form.value.email.trim(),
	})
}
</script>

<template>
	<Dialog v-model:open="open" title="Add speaker" size="md">
		<template #default>
			<div class="space-y-4">
				<div class="flex gap-3">
					<FormControl v-model="form.first_name" class="flex-1" label="First name" required />
					<FormControl v-model="form.last_name" class="flex-1" label="Last name" />
				</div>
				<FormControl
					v-model="form.email"
					type="email"
					label="Email"
					required
					@keyup.enter="submit"
				/>
				<p v-if="alreadyListed" class="text-base text-ink-red-6">
					That email is already a speaker on this proposal.
				</p>
			</div>
		</template>

		<template #actions>
			<div class="flex justify-end gap-2">
				<Button label="Cancel" @click="open = false" />
				<Button
					variant="solid"
					label="Add speaker"
					:disabled="!canSubmit"
					:loading="saving"
					@click="submit"
				/>
			</div>
		</template>
	</Dialog>
</template>
