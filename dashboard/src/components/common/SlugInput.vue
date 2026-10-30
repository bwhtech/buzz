<script setup lang="ts">
import { watch } from "vue"

import PrefixedInput from "@/components/common/PrefixedInput.vue"
import SlugStatus from "@/components/common/SlugStatus.vue"
import { type Availability, useSlugAvailability } from "@/composables/useSlugAvailability"

export type { Availability }

const props = defineProps<{
	prefix: string
	label: string
	placeholder?: string
	disabled?: boolean
	savedSlug?: string | null
	check: (slug: string) => Promise<Availability | null>
}>()
const slug = defineModel<string>({ required: true })
const availability = defineModel<Availability | null>("availability", { default: null })

const live = useSlugAvailability(slug, props.check, () => props.savedSlug)
watch(live.availability, (value) => (availability.value = value), { immediate: true })
</script>

<template>
	<div>
		<PrefixedInput
			v-model="slug"
			:prefix="prefix"
			:label="label"
			:placeholder="placeholder"
			:disabled="disabled"
		/>
		<SlugStatus
			class="pt-1.5 text-sm"
			:checking="live.checking.value"
			:availability="live.availability.value"
		/>
	</div>
</template>
