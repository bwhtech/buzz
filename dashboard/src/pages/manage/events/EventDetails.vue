<script setup lang="ts">
import { useMyEvent } from "@/data/events";
import { Breadcrumbs, PageHeader } from "frappe-ui";
import { computed } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
const eventId = computed(() => route.params.eventId as string);

const event = useMyEvent(eventId);

// The event, then the section of it being looked at. Neither crumb is a link: the
// event on its own resolves to this very page.
const items = computed(() => [{ label: event.value?.title || "Event" }, { label: "Details" }]);
</script>

<template>
	<PageHeader class="border-none pt-2 bg-surface-elevation-1">
		<Breadcrumbs :items="items" />
	</PageHeader>

	<div class="m-auto max-w-[800px] w-full py-8 px-4 space-y-6">
		<h1 class="font-semibold text-4xl">{{ event?.title || "Details" }}</h1>
	</div>
</template>
