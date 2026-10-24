<script setup lang="ts">
import {
	Button,
	Dialog,
	ErrorMessage,
	FormControl,
	MultiSelect,
	Switch,
	TextInput,
	dialog,
	toast,
} from "frappe-ui"
import { computed, reactive, ref, watch } from "vue"

import { serverErrorMessage } from "@/utils/serverError"

import {
	type CheckInZone,
	type CheckInZoneList,
	REPEAT_RULES,
	type RepeatRule,
} from "./checkInZones"

const props = defineProps<{
	event: string
	// null opens the dialog on a new zone.
	zone: CheckInZone | null
	zones: CheckInZoneList
	ticketTypes: { name: string; title: string }[]
}>()
const open = defineModel<boolean>("open", { required: true })

const form = reactive({
	title: "",
	repeat_rule: REPEAT_RULES[0] as RepeatRule,
	enabled: true,
	ticket_types: [] as string[],
})
const errorMessage = ref("")

const isNew = computed(() => !props.zone)
const isDefault = computed(() => !!props.zone?.is_default)
const isSaving = computed(() => props.zones.insert.loading || props.zones.setValue.loading)

const repeatRuleOptions = REPEAT_RULES.map((rule) => ({ label: __(rule), value: rule }))
const ticketTypeOptions = computed(() =>
	props.ticketTypes.map((row) => ({ label: row.title, value: row.name })),
)

watch(open, (opened) => {
	if (!opened) return
	errorMessage.value = ""
	Object.assign(form, {
		title: props.zone?.title ?? "",
		repeat_rule: props.zone?.repeat_rule ?? REPEAT_RULES[0],
		enabled: props.zone ? !!props.zone.enabled : true,
		ticket_types: props.zone?.ticket_types.map((row) => row.ticket_type) ?? [],
	})
})

async function save() {
	const values = {
		title: form.title.trim(),
		repeat_rule: form.repeat_rule,
		enabled: form.enabled ? (1 as const) : (0 as const),
		ticket_types: form.ticket_types.map((ticket_type) => ({ ticket_type })),
	}
	const request = props.zone
		? props.zones.setValue.submit({ ...values, name: props.zone.name })
		: props.zones.insert.submit({ ...values, event: props.event })
	await request.catch(() => null)
	const error = props.zone ? props.zones.setValue.error : props.zones.insert.error
	if (error) return (errorMessage.value = serverErrorMessage(error))
	toast.success(props.zone ? __("Zone saved") : __("Zone added"))
	open.value = false
}

function confirmDelete() {
	dialog.confirm({
		title: __("Delete zone"),
		message: __("Delete {0}? A zone with check-ins cannot be deleted, disable it instead.", [
			props.zone?.title,
		]),
		theme: "red",
		confirmLabel: __("Delete"),
		onConfirm: remove,
	})
}

async function remove() {
	await props.zones.delete.submit({ name: props.zone?.name ?? "" }).catch(() => null)
	if (props.zones.delete.error) throw props.zones.delete.error
	toast.success(__("Zone deleted"))
	open.value = false
}
</script>

<template>
	<Dialog v-model="open" :title="isNew ? __('Add zone') : __('Edit zone')">
		<div class="flex flex-col gap-4">
			<TextInput v-model="form.title" :label="__('Title')" :placeholder="__('Workshop hall')" />
			<FormControl
				v-model="form.repeat_rule"
				type="select"
				:label="__('Repeat rule')"
				:options="repeatRuleOptions"
			/>
			<MultiSelect
				v-model="form.ticket_types"
				:label="__('Ticket types')"
				:options="ticketTypeOptions"
				:placeholder="__('All tickets')"
			/>
			<Switch
				v-model="form.enabled"
				padded
				:label="__('Enabled')"
				:description="
					isDefault
						? __('The default zone cannot be disabled.')
						: __('Disabled zones are hidden from the check-in scanner.')
				"
				:disabled="isDefault"
			/>
			<ErrorMessage v-if="errorMessage" :message="errorMessage" />
		</div>

		<template #actions>
			<div class="flex w-full items-center gap-2">
				<Button
					v-if="!isNew && !isDefault"
					theme="red"
					:label="__('Delete')"
					@click="confirmDelete"
				/>
				<div class="ml-auto flex gap-2">
					<Button :label="__('Cancel')" @click="open = false" />
					<Button
						variant="solid"
						:label="__('Save')"
						:disabled="!form.title.trim()"
						:loading="isSaving"
						@click="save"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>
