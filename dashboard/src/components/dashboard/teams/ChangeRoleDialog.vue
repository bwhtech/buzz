<script setup lang="ts">
import { Button, Dialog, ErrorMessage, FormControl, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { useChangeRoles } from "@/data/teams"
import type { TeamMember } from "@/types"
import { ASSIGNABLE_TEAM_ROLES } from "@/utils/teamRoles"

// A selection of one is how a single row's action arrives, so there is one dialog.
const props = defineProps<{ team: string; members: TeamMember[] }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ success: [] }>()

const changeRoles = useChangeRoles()
const role = ref("")
// `useCall`'s own reset only drops the submitted params, so a failure would otherwise still
// be on screen the next time the dialog opens.
const errorMessage = ref("")

const only = computed(() => (props.members.length === 1 ? props.members[0] : null))

const name = computed(() => only.value?.full_name || only.value?.user || "")

const description = computed(() =>
	only.value
		? __("{0} keeps their place on the team, with a different set of permissions.", [name.value])
		: __("All {0} keep their place on the team, with a different set of permissions.", [
				props.members.length,
			]),
)

// The panel's role legend explains the roles; this only guards a pointless save.
const unchanged = computed(
	() =>
		!props.members.length ||
		!role.value ||
		props.members.every((member) => member.team_role === role.value),
)

// The selection arrives with the dialog, so the select is seeded on open rather than on mount.
watch(isOpen, (open) => {
	if (!open) return
	role.value = sharedRole()
	errorMessage.value = ""
})

// A mixed selection has no role to show, so it starts blank rather than on someone's.
function sharedRole() {
	const roles = new Set(props.members.map((member) => member.team_role))
	return roles.size === 1 ? [...roles][0] : ""
}

async function submit() {
	if (unchanged.value) return

	const users = props.members.map((member) => member.user)
	await changeRoles.submit({ team: props.team, users, team_role: role.value })
	// useCall settles either way, so the failure has to be read off the composable.
	if (changeRoles.error) {
		errorMessage.value = changeRoles.error.message
		return
	}

	const done = only.value
		? __("{0} is now {1}.", [name.value, role.value])
		: __("{0} members are now {1}.", [users.length, role.value])

	emit("success")
	isOpen.value = false
	toast.success(done)
}
</script>

<template>
	<Dialog v-model="isOpen" :title="__('Change role')">
		<div class="space-y-3">
			<p class="text-base text-ink-gray-5">{{ description }}</p>

			<FormControl
				v-model="role"
				type="select"
				:label="__('Role')"
				:options="ASSIGNABLE_TEAM_ROLES"
			/>

			<ErrorMessage :message="errorMessage" />
		</div>

		<template #actions="{ close }">
			<div class="flex gap-2">
				<Button
					variant="solid"
					:label="__('Save')"
					:loading="changeRoles.loading"
					:disabled="unchanged"
					@click="submit"
				/>
				<Button variant="outline" :label="__('Cancel')" @click="close" />
			</div>
		</template>
	</Dialog>
</template>
