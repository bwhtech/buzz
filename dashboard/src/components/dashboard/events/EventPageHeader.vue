<script setup lang="ts">
import { Breadcrumbs, PageHeader } from "frappe-ui"
import { computed } from "vue"

// The event, then the section of it being looked at. Neither crumb is a link: the
// event on its own resolves to whichever section is open.
const props = defineProps<{ title: string | null | undefined; section: string }>()

const items = computed(() => [{ label: props.title || "Event" }, { label: props.section }])
</script>

<template>
	<PageHeader class="border-none pt-2 bg-surface-elevation-1">
		<Breadcrumbs :items="items" />
		<slot />
	</PageHeader>
</template>
