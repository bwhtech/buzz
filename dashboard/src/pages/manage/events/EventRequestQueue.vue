<script setup lang="ts">
import type { RequestType } from "@/types"

import EventRequests from "./EventRequests.vue"

defineProps<{ requestType: RequestType }>()
</script>

<template>
	<!-- Approvals and Waitlist share one page; the key remounts it when moving between them. -->
	<EventRequests :key="requestType" :request-type="requestType" />
</template>
