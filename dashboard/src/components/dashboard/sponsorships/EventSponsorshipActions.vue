<script setup lang="ts">
import { computed, ref } from "vue"

import QuickActionsRail, {
	type QuickAction,
} from "@/components/dashboard/events/QuickActionsRail.vue"
import EnquiryFormDialog from "@/components/dashboard/sponsorships/EnquiryFormDialog.vue"
import type { EnquiryFormState } from "@/types"

const props = defineProps<{ form: EnquiryFormState; canWrite: boolean }>()
const emit = defineEmits<{ changed: [] }>()

const dialogOpen = ref(false)

const actions = computed<QuickAction[]>(() =>
	[
		props.form.link
			? { icon: "lucide-arrow-up-right", label: "Go to form page", link: props.form.link }
			: null,
		{
			icon: "lucide-square-pen",
			label: "Edit form",
			link: `/app/sponsor-enquiry-form/${props.form.name}`,
		},
	].filter((action) => action !== null),
)
</script>

<template>
	<QuickActionsRail
		subject="Enquiry Form"
		open-icon="lucide-globe"
		closed-icon="lucide-globe-off"
		:closed="form.closed"
		:can-write="canWrite"
		:actions="actions"
		@toggle="dialogOpen = true"
	/>

	<EnquiryFormDialog
		v-model="dialogOpen"
		:form="form.name"
		:closed="form.closed"
		@changed="emit('changed')"
	/>
</template>
