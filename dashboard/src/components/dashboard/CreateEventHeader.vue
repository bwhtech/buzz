<script setup lang="ts">
import { Button, PageHeader } from "frappe-ui"
</script>

<template>
	<PageHeader class="border-none pt-2 bg-surface-elevation-1">
		<Button
			class="ml-auto"
			variant="solid"
			icon-left="plus"
			label="Create Event"
			:route="{ name: 'create-event' }"
		/>
	</PageHeader>
</template>
