<script setup lang="ts">
import { Button, Dialog, FormControl } from "frappe-ui"
import { computed, reactive, ref, watch } from "vue"

import type { EventExternalLink } from "@/types"
import { LINK_ICONS, isValidUrl, normalizeUrl, suggestLink } from "@/utils/eventLinks"

const props = defineProps<{ link: EventExternalLink | null }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ submit: [link: EventExternalLink]; remove: [] }>()

const draft = reactive({ icon: "", label: "", url: "" })
const showErrors = ref(false)
let suggestedLabel = ""
let iconChosen = false

watch(isOpen, (open) => {
	if (!open) return
	Object.assign(draft, {
		icon: props.link?.icon ?? "",
		label: props.link?.label ?? "",
		url: props.link?.url ?? "",
	})
	showErrors.value = false
	suggestedLabel = ""
	iconChosen = !!props.link
})

watch(
	() => draft.url,
	(url) => {
		const suggestion = suggestLink(url)
		if (!suggestion) return
		if (!draft.label || draft.label === suggestedLabel) {
			draft.label = suggestion.label
			suggestedLabel = suggestion.label
		}
		if (!iconChosen) draft.icon = suggestion.icon
	},
)

const urlError = computed(() => {
	if (!draft.url.trim()) return __("Add the address people should open.")
	return isValidUrl(draft.url) ? "" : __("That doesn't look like a web address.")
})
const labelError = computed(() =>
	draft.label.trim() ? "" : __("Give the link a name attendees will recognise."),
)

function chooseIcon(icon: string) {
	iconChosen = true
	draft.icon = icon
}

function submit() {
	showErrors.value = true
	if (urlError.value || labelError.value) return
	emit("submit", { icon: draft.icon, label: draft.label.trim(), url: normalizeUrl(draft.url) })
	isOpen.value = false
}

function submitOnEnter(event: KeyboardEvent) {
	if (!(event.target instanceof HTMLInputElement)) return
	event.preventDefault()
	submit()
}

function remove() {
	emit("remove")
	isOpen.value = false
}
</script>

<template>
	<Dialog v-model="isOpen" :title="link ? __('Edit link') : __('Add link')">
		<form novalidate class="space-y-4" @submit.prevent @keydown.enter="submitOnEnter">
			<FormControl
				v-model="draft.url"
				:label="__('URL')"
				placeholder="https://"
				autocomplete="off"
				:error="showErrors ? urlError : undefined"
			/>

			<FormControl
				v-model="draft.label"
				:label="__('Label')"
				placeholder="Venue on Google Maps"
				:error="showErrors ? labelError : undefined"
			/>

			<div class="space-y-1.5">
				<p class="text-xs text-ink-gray-5">{{ __("Icon") }}</p>
				<div class="grid grid-cols-7 gap-1" role="group" :aria-label="__('Icon')">
					<Button
						v-for="option in LINK_ICONS"
						:key="option.value"
						type="button"
						:aria-pressed="draft.icon === option.value"
						:aria-label="__(option.label)"
						:title="__(option.label)"
						:icon="option.icon"
						:variant="draft.icon === option.value ? 'subtle' : 'ghost'"
						@click="chooseIcon(option.value)"
					/>
				</div>
			</div>

			<div class="flex items-center gap-2 pt-2">
				<Button
					v-if="link"
					type="button"
					variant="ghost"
					theme="red"
					icon-left="lucide-trash-2"
					:label="__('Remove')"
					@click="remove"
				/>
				<Button type="button" class="ml-auto" :label="__('Cancel')" @click="isOpen = false" />
				<Button
					type="button"
					variant="solid"
					:label="link ? __('Update') : __('Add link')"
					@click="submit"
				/>
			</div>
		</form>
	</Dialog>
</template>
