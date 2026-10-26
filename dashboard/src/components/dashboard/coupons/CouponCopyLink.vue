<script setup lang="ts">
import { Button } from "frappe-ui"

import { useCopyToClipboard } from "@/composables/useCopyToClipboard"
import { accessCodeLink } from "@/utils/couponLabels"

const props = defineProps<{ code: string; registrationLink: string | null }>()

const copyToClipboard = useCopyToClipboard()
const copyLink = () =>
	props.registrationLink &&
	copyToClipboard(accessCodeLink(props.registrationLink, props.code), "Link copied")
</script>

<template>
	<Button
		v-if="registrationLink"
		variant="ghost"
		icon="lucide-link"
		label="Copy link"
		tooltip="Copy link"
		@click="copyLink"
	/>
</template>
