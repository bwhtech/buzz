<script setup lang="ts">
import { ErrorMessage, Skeleton, toast } from "frappe-ui"
import { computed, reactive, watch } from "vue"
import { useRoute } from "vue-router"

import SaveActions from "@/components/dashboard/teams/SaveActions.vue"
import TeamPageHeader from "@/components/dashboard/teams/TeamPageHeader.vue"
import TeamTaxDetailsForm from "@/components/dashboard/teams/TeamTaxDetailsForm.vue"
import { useSaveShortcut } from "@/composables/useSaveShortcut"
import { updateTaxDetails, useTeamOverview } from "@/data/teams"
import type { TeamTaxDetails } from "@/types"
import { serverErrorMessage } from "@/utils/serverError"
import { canManageMembers } from "@/utils/teamRoles"

const route = useRoute()
const team = route.params.teamId as string
const overview = useTeamOverview(team)

// Owner/Admin, the same rule update_tax_details checks.
const canEdit = computed(() => canManageMembers(overview.data?.my_role))

const formFromDetails = (details?: TeamTaxDetails) => ({
	legal_name: details?.legal_name ?? "",
	tax_id: details?.tax_id ?? "",
	billing_address: details?.billing_address ?? "",
})

const form = reactive(formFromDetails())
watch(
	() => overview.data,
	(data) => data && Object.assign(form, formFromDetails(data.tax_details)),
	{ immediate: true },
)

const isDirty = computed(
	() =>
		Boolean(overview.data) &&
		JSON.stringify(form) !== JSON.stringify(formFromDetails(overview.data?.tax_details)),
)

async function save() {
	if (!isDirty.value || updateTaxDetails.loading) return
	await updateTaxDetails.submit({ team, ...form }).catch(() => null)
	if (updateTaxDetails.error) return
	await overview.reload()
	toast.success(__("Tax details saved"))
}

const discard = () => Object.assign(form, formFromDetails(overview.data?.tax_details))

useSaveShortcut(save, isDirty)
</script>

<template>
	<TeamPageHeader section="Payments">
		<SaveActions
			v-if="canEdit"
			:is-dirty="isDirty"
			:saving="updateTaxDetails.loading"
			@save="save"
			@discard="discard"
		/>
	</TeamPageHeader>

	<div class="m-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-8 max-md:pb-24">
		<ErrorMessage
			v-if="overview.error || updateTaxDetails.error"
			:message="serverErrorMessage(overview.error || updateTaxDetails.error)"
		/>

		<Skeleton v-if="!overview.data && !overview.error" class="h-64 w-full rounded-5" />

		<TeamTaxDetailsForm v-else-if="overview.data" v-model="form" :editable="canEdit" />
	</div>
</template>
