<script setup lang="ts">
import { watch } from "vue"

import LoginDialog from "@/components/LoginDialog.vue"
import { useLoginDialog } from "@/composables/useLoginDialog"

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ "update:open": [value: boolean] }>()

// LoginDialog opens from the shared composable; the island opens it through its prop.
const { is_open } = useLoginDialog()
watch(
	() => props.open,
	(value) => (is_open.value = value),
	{ immediate: true },
)
watch(is_open, (value) => emit("update:open", value))
</script>

<template>
	<LoginDialog />
</template>
