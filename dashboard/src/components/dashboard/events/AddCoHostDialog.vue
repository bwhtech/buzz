<script setup lang="ts">
import { Button, Dialog, ErrorMessage, FormControl, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"

import AvatarUploader from "@/components/common/AvatarUploader.vue"
import { useAddCoHost } from "@/data/events"
import type { FrappeError } from "@/types"

const props = defineProps<{ event: string }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ added: [] }>()

const hostName = ref("")
const logo = ref<string | null>(null)
const byLine = ref("")
const about = ref("")
const showErrors = ref(false)

const addCoHost = useAddCoHost()
const errorMessage = computed(() => (addCoHost.error as FrappeError | null)?.message)

watch(isOpen, (open) => {
	if (!open) return
	hostName.value = ""
	logo.value = null
	byLine.value = ""
	about.value = ""
	showErrors.value = false
})

const invalid = computed(() => !hostName.value.trim())

watch(hostName, () => (showErrors.value = false))

async function submit() {
	showErrors.value = true
	if (invalid.value) return

	await addCoHost.submit({
		event: props.event,
		host_name: hostName.value.trim(),
		logo: logo.value ?? undefined,
		by_line: byLine.value.trim() || undefined,
		about: about.value.trim() || undefined,
	})
	if (addCoHost.error) return

	toast.success(__("{0} was added as a co-host.", [hostName.value.trim()]))
	emit("added")
	isOpen.value = false
}
</script>

<template>
	<Dialog v-model="isOpen" :title="__('Add Co-host')">
		<form novalidate class="space-y-4" @submit.prevent="submit">
			<AvatarUploader
				v-model="logo"
				shape="square"
				:label="__('Co-host logo')"
				:title="__('Logo')"
				:description="__('Shown beside the name under Hosted by.')"
			/>

			<FormControl
				v-model="hostName"
				:label="__('Name')"
				placeholder="Acme Corp"
				autocomplete="off"
			/>

			<FormControl v-model="byLine" :label="__('By line')" placeholder="Community partner" />

			<FormControl
				v-model="about"
				type="textarea"
				:label="__('About')"
				placeholder="What do they do?"
			/>

			<p v-if="showErrors && invalid" class="text-sm text-ink-red-4">
				{{ __("A co-host needs a name.") }}
			</p>
			<ErrorMessage v-else-if="showErrors && errorMessage" :message="errorMessage" />

			<!-- type=button: inside a form a submit button fires `submit` twice, and the
				 second call adds the co-host again. -->
			<Button
				type="button"
				variant="solid"
				:label="__('Add Co-host')"
				class="w-full"
				:loading="addCoHost.loading"
				@click="submit"
			/>
		</form>
	</Dialog>
</template>
