<script setup lang="ts">
import { useEventListener } from "@vueuse/core"
import { ErrorMessage, Spinner } from "frappe-ui"
import { ref } from "vue"
import { onBeforeRouteLeave, useRoute } from "vue-router"

import BuildCanvas from "@/components/dashboard/form-builder/build/BuildCanvas.vue"
import { useQuestionEditor } from "@/components/dashboard/form-builder/build/useQuestionEditor"
import FormBuilderLayout from "@/components/dashboard/form-builder/FormBuilderLayout.vue"
import LogicTab from "@/components/dashboard/form-builder/logic/LogicTab.vue"
import { emptyRule } from "@/components/dashboard/form-builder/logic/ruleOptions"
import SettingsTab from "@/components/dashboard/form-builder/settings/SettingsTab.vue"
import {
	type FormQuestion,
	useFormBuilder,
} from "@/components/dashboard/form-builder/useFormBuilder"
import type { FrappeError } from "@/types"

const route = useRoute()
const eventId = route.params.eventId as string
const builder = useFormBuilder(() => route.params.formName as string)
const { draft } = builder
const tab = ref("build")
const editor = useQuestionEditor(
	() => draft.value!.questions,
	() => draft.value!.logic_rules,
)

function addRuleFor(question: FormQuestion) {
	draft.value!.logic_rules.push(emptyRule(editor.ensureFieldname(question)))
	tab.value = "logic"
}

const UNSAVED = "Leave without saving? Your changes to this form will be lost."
onBeforeRouteLeave(() => !builder.dirty.value || window.confirm(UNSAVED))
useEventListener(window, "beforeunload", (event) => builder.dirty.value && event.preventDefault())
</script>

<template>
	<FormBuilderLayout v-model:tab="tab" :builder="builder" :event-id="eventId">
		<div v-if="builder.form.error" class="p-8">
			<ErrorMessage :message="(builder.form.error as FrappeError).message" />
		</div>
		<div v-else-if="!draft" class="grid h-full place-items-center">
			<Spinner class="size-5" />
		</div>
		<BuildCanvas
			v-else-if="tab === 'build'"
			v-model="draft"
			:doctype-fields="builder.doctypeFields.value"
			:editor="editor"
			@add-rule="addRuleFor"
		/>
		<LogicTab
			v-else-if="tab === 'logic'"
			v-model="draft"
			:doctype-fields="Object.values(builder.doctypeFields.value)"
			:editor="editor"
		/>
		<SettingsTab v-else-if="tab === 'settings'" v-model="draft" :event-id="eventId" />
	</FormBuilderLayout>
</template>
