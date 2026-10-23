<script setup lang="ts">
import { Badge } from "frappe-ui"
import { ref, useId } from "vue"

import EmailChipsInput from "@/components/dashboard/events/collaborators/EmailChipsInput.vue"

defineProps<{
	label: string
	// Recipients the row shows but does not let you remove, such as a proposal's speakers.
	fixed?: string[]
}>()

const addresses = defineModel<string[]>({ default: () => [] })
const draft = ref("")
const id = useId()
</script>

<template>
	<div class="flex min-h-[30px] items-center gap-1.5 pr-2.5 pl-3">
		<label :for="id" class="w-[30px] shrink-0 text-sm text-ink-gray-5">{{ label }}</label>
		<div v-if="fixed" class="flex flex-1 flex-wrap gap-1">
			<Badge v-for="name in fixed" :key="name" size="lg" theme="gray" :label="name" />
		</div>
		<EmailChipsInput
			v-else
			:id="id"
			v-model="addresses"
			v-model:draft="draft"
			:rejected="() => ''"
			bare
			class="flex-1"
		/>
		<slot />
	</div>
</template>
