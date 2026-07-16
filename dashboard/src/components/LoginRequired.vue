<template>
	<div class="flex flex-col items-center justify-center py-16 px-4">
		<div class="text-center max-w-md">
			<h2 class="text-xl font-semibold text-ink-gray-8 mb-2">
				{{ __("Login Required") }}
			</h2>
			<p class="text-ink-gray-6 mb-6">
				{{ __(message) }}
			</p>
			<Button variant="solid" size="lg" @click="openLogin">{{ __("Log In") }}</Button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useLoginDialog } from "@/composables/useLoginDialog";
import { Button } from "frappe-ui";

withDefaults(
	defineProps<{
		message?: string;
	}>(),
	{
		message: "Please log in to continue.",
	}
);

const { open: openLogin } = useLoginDialog();
</script>
