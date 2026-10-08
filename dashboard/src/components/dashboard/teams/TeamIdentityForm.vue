<script setup lang="ts">
import { ErrorMessage, FormControl, toast } from "frappe-ui"
import { computed, reactive, watch } from "vue"

import AvatarUploader from "@/components/common/AvatarUploader.vue"
import { updateTeam } from "@/data/teams"
import type { TeamOverview } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"

const props = defineProps<{ team: TeamOverview }>()
const emit = defineEmits<{ saved: [] }>()

const form = reactive({ team_name: props.team.team_name, logo: props.team.logo })

watch(
	() => props.team,
	(team) => Object.assign(form, { team_name: team.team_name, logo: team.logo }),
)

const isDirty = computed(
	() => form.team_name !== props.team.team_name || form.logo !== props.team.logo,
)

// A logo has no blur: an upload or a remove is the whole gesture.
watch(() => form.logo, save)

async function save() {
	if (!isDirty.value || !form.team_name.trim()) return

	await updateTeam.submit({ team: props.team.name, ...form }).catch(() => null)
	if (updateTeam.error) return

	emit("saved")
	toast.success(__("Team updated"))
}
</script>

<template>
	<AvatarUploader
		v-model="form.logo"
		shape="square"
		:label="form.team_name"
		:title="__('Team logo')"
		:description="__('Shown wherever the team appears')"
	/>

	<FormControl
		type="text"
		class="max-w-sm"
		:label="__('Team Name')"
		v-model="form.team_name"
		:maxlength="140"
		@blur="save"
	/>

	<ErrorMessage :message="serverErrorMessage(updateTeam.error)" />
</template>
