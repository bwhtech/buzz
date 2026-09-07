<script setup lang="ts">
import { Button, Dialog, ErrorMessage, FormControl, toast } from "frappe-ui"
import { computed, ref, watch } from "vue"

import { useChangeRole } from "@/data/teams"
import type { TeamMember } from "@/types"
import { ASSIGNABLE_TEAM_ROLES } from "@/utils/teamRoles"

const props = defineProps<{ team: string; member: TeamMember | null }>()
const isOpen = defineModel<boolean>({ required: true })
const emit = defineEmits<{ success: [] }>()

const changeRole = useChangeRole()
const role = ref("")
// `useCall`'s own reset only drops the submitted params, so a failure would otherwise still
// be on screen the next time the dialog opens.
const errorMessage = ref("")

const name = computed(() => props.member?.full_name || props.member?.user || "")

// The panel's role legend explains the roles; this only guards a pointless save.
const unchanged = computed(() => !props.member || role.value === props.member.team_role)

// The member arrives with the dialog, so the select is seeded on open rather than on mount.
watch(isOpen, (open) => {
	if (!open) return
	role.value = props.member?.team_role ?? ""
	errorMessage.value = ""
})

async function submit() {
	if (!props.member || unchanged.value) return

	await changeRole.submit({ team: props.team, user: props.member.user, team_role: role.value })
	// useCall settles either way, so the failure has to be read off the composable.
	if (changeRole.error) {
		errorMessage.value = changeRole.error.message
		return
	}

	emit("success")
	isOpen.value = false
	toast.success(__("{0} is now {1}.", [name.value, role.value]))
}
</script>

<template>
	<Dialog v-model="isOpen" :title="__('Change role')">
		<div class="space-y-3">
			<p class="text-base text-ink-gray-5">
				{{ __("{0} keeps their place on the team, with a different set of permissions.", [name]) }}
			</p>

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
					:loading="changeRole.loading"
					:disabled="unchanged"
					@click="submit"
				/>
				<Button variant="outline" :label="__('Cancel')" @click="close" />
			</div>
		</template>
	</Dialog>
</template>
