<script setup lang="ts">
import { useEventListener } from "@vueuse/core"
import { ErrorMessage, Spinner, TabButtons } from "frappe-ui"
import { computed, ref, watch } from "vue"
import { onBeforeRouteLeave, useRoute } from "vue-router"

import BuildCanvas from "@/components/dashboard/form-builder/build/BuildCanvas.vue"
import { useQuestionEditor } from "@/components/dashboard/form-builder/build/useQuestionEditor"
import FormBuilderLayout from "@/components/dashboard/form-builder/FormBuilderLayout.vue"
import LogicTab from "@/components/dashboard/form-builder/logic/LogicTab.vue"
import SettingsTab from "@/components/dashboard/form-builder/settings/SettingsTab.vue"
import { useFormBuilder } from "@/components/dashboard/form-builder/useFormBuilder"
import type { FrappeError } from "@/types"

const route = useRoute()
const eventId = route.params.eventId as string
const builder = useFormBuilder(() => route.params.formName as string)
// Registration edits the event's attendee questions on the same page.
const attendee = useFormBuilder(() => builder.attendeeForm.value)
const isRegistration = computed(() => !!builder.attendeeForm.value)
const builders = computed(() => (isRegistration.value ? [builder, attendee] : [builder]))

const SCOPES = [
	{ label: "Attendees · each ticket", value: "attendee" },
	{ label: "Booking · once", value: "booking" },
]
const FIXED_FIELDS: Record<string, string[]> = {
	attendee: ["First name", "Last name", "Email"],
	booking: ["Name", "Email"],
}
const scope = ref("attendee")
const active = computed(() =>
	isRegistration.value && scope.value === "attendee" ? attendee : builder,
)
const draft = computed(() => active.value.draft.value)

const tab = ref("build")
const device = ref<"desktop" | "mobile">("desktop")
const preview = ref(false)
const editor = useQuestionEditor(
	() => draft.value!.questions,
	() => draft.value!.logic_rules,
)
watch(scope, () => (editor.selected.value = null))

const dirty = computed(() => builders.value.some((one) => one.dirty.value))
const UNSAVED = "Leave without saving? Your changes to this form will be lost."
onBeforeRouteLeave(() => !dirty.value || window.confirm(UNSAVED))
useEventListener(window, "beforeunload", (event) => dirty.value && event.preventDefault())
</script>

<template>
	<FormBuilderLayout
		v-model:tab="tab"
		v-model:device="device"
		v-model:preview="preview"
		:builders="builders"
		:event-id="eventId"
	>
		<div v-if="active.form.error" class="p-8">
			<ErrorMessage :message="(active.form.error as FrappeError).message" />
		</div>
		<div v-else-if="!draft" class="grid h-full place-items-center">
			<Spinner class="size-5" />
		</div>
		<div v-else class="flex h-full flex-col">
			<div
				v-if="isRegistration && tab !== 'settings'"
				class="flex justify-center bg-surface-base pt-3"
			>
				<TabButtons v-model="scope" :options="SCOPES" />
			</div>
			<div class="min-h-0 flex-1">
				<BuildCanvas
					v-if="tab === 'build'"
					:key="scope"
					v-model="active.draft.value!"
					:doctype-fields="active.doctypeFields.value"
					:editor="editor"
					:device="device"
					:preview="preview"
					:fixed-fields="isRegistration ? FIXED_FIELDS[scope] : undefined"
					@open-logic="tab = 'logic'"
				/>
				<LogicTab
					v-else-if="tab === 'logic'"
					:key="scope"
					v-model="active.draft.value!"
					:doctype-fields="Object.values(active.doctypeFields.value)"
					:editor="editor"
					@open-build="tab = 'build'"
				/>
				<SettingsTab v-else v-model="builder.draft.value!" :event-id="eventId" />
			</div>
		</div>
	</FormBuilderLayout>
</template>
