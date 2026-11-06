<script setup lang="ts">
import {
	Button,
	ErrorMessage,
	FormLabel,
	Switch,
	TabButtons,
	TextInput,
	dialog,
	toast,
} from "frappe-ui"
import { computed, reactive, ref, watch } from "vue"

import {
	Drawer,
	DrawerCloseButton,
	DrawerContent,
	DrawerDescription,
	DrawerTitle,
} from "@/components/common/drawer"
import { serverErrorMessage } from "@/utils/serverError"

import {
	type CheckInZone,
	type CheckInZoneList,
	REPEAT_RULES,
	type RepeatRule,
} from "./checkInZones"

const props = defineProps<{
	event: string
	// null opens the drawer on a new zone.
	zone: CheckInZone | null
	zones: CheckInZoneList
	ticketTypes: { name: string; title: string }[]
}>()
const open = defineModel<boolean>("open", { required: true })
const emit = defineEmits<{ saved: [] }>()

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
const repeatRuleHelp = computed(() =>
	form.repeat_rule === "Once per event"
		? __("A guest checks in here once for the whole event.")
		: __("A guest can check in here again each day of the event."),
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

function toggleTicketType(name: string) {
	const index = form.ticket_types.indexOf(name)
	if (index === -1) form.ticket_types.push(name)
	else form.ticket_types.splice(index, 1)
}

async function save() {
	if (!form.title.trim() || isSaving.value) return
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
	emit("saved")
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
	emit("saved")
	open.value = false
}
</script>

<template>
	<Drawer v-model:open="open" swipe-direction="right">
		<DrawerContent>
			<div
				class="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-outline-gray-1 pl-5 pr-2.5"
			>
				<DrawerTitle class="text-lg font-semibold text-ink-gray-9">
					{{ isNew ? __("Add zone") : __("Edit zone") }}
				</DrawerTitle>
				<DrawerDescription class="sr-only">
					{{ __("A zone is a place at the venue where guests are checked in.") }}
				</DrawerDescription>
				<DrawerCloseButton />
			</div>

			<div
				class="flex flex-1 flex-col gap-5 overflow-y-auto overscroll-contain p-5"
				@keydown.meta.enter.prevent="save"
				@keydown.ctrl.enter.prevent="save"
			>
				<TextInput
					v-model="form.title"
					:label="__('Name')"
					:placeholder="__('e.g. Lunch, Workshop room')"
				/>

				<div class="flex flex-col gap-1.5">
					<FormLabel :label="__('Repeat rule')" />
					<TabButtons v-model="form.repeat_rule" fluid :options="repeatRuleOptions" />
					<span class="text-p-xs text-ink-gray-5">{{ repeatRuleHelp }}</span>
				</div>

				<div v-if="ticketTypes.length" class="flex flex-col gap-1.5">
					<FormLabel :label="__('Allowed tickets')" />
					<div class="flex flex-wrap gap-1.5">
						<Button
							v-for="ticketType in ticketTypes"
							:key="ticketType.name"
							class="duration-150 ease-out active:scale-[0.97] !transition-[transform,background-color,color]"
							:variant="form.ticket_types.includes(ticketType.name) ? 'solid' : 'outline'"
							:label="ticketType.title"
							:aria-pressed="form.ticket_types.includes(ticketType.name)"
							@click="toggleTicketType(ticketType.name)"
						/>
					</div>
					<span class="text-p-xs text-ink-gray-5">
						{{
							form.ticket_types.length
								? __("Only these tickets can check in here.")
								: __("Every ticket can check in here. Pick some to limit the zone.")
						}}
					</span>
				</div>

				<div class="border-t border-outline-gray-1 pt-4">
					<Switch
						v-model="form.enabled"
						:label="__('Enabled')"
						:description="
							isDefault
								? __('The default zone can be renamed but not turned off.')
								: __('Turned-off zones are hidden from the check-in page.')
						"
						:disabled="isDefault"
					/>
				</div>

				<ErrorMessage :message="errorMessage" />
			</div>

			<template #footer>
				<Button
					v-if="!isNew && !isDefault"
					variant="ghost"
					theme="red"
					icon-left="lucide-trash-2"
					:label="__('Delete')"
					@click="confirmDelete"
				/>
				<div class="ml-auto flex gap-2">
					<Button variant="subtle" :label="__('Cancel')" @click="open = false" />
					<Button
						variant="solid"
						:label="isNew ? __('Add zone') : __('Save')"
						:disabled="!form.title.trim()"
						:loading="isSaving"
						@click="save"
					/>
				</div>
			</template>
		</DrawerContent>
	</Drawer>
</template>
