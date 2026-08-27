<template>
	<div
		class="min-h-screen bg-surface-base text-ink-gray-8"
		:class="{ 'h-screen overflow-hidden': fullBleed }"
	>
		<Navbar v-if="!fullBleed" />
		<div :class="fullBleed ? 'h-full' : 'max-w-4xl py-8 px-4 md:py-12 mx-auto'">
			<div v-if="!routerReady" class="flex justify-center py-16">
				<Spinner class="w-8 h-8" />
			</div>
			<LoginRequired v-else-if="requires_auth && !session.isLoggedIn" />
			<slot v-else></slot>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Spinner } from "frappe-ui"
import { computed, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import LoginRequired from "@/components/LoginRequired.vue"
import Navbar from "@/components/Navbar.vue"
import { session } from "@/data/session"

const route = useRoute()
const router = useRouter()
const routerReady = ref(false)
const requires_auth = computed(() => !route.meta?.isPublic)
const fullBleed = computed(() => Boolean(route.meta?.fullBleed))

router.isReady().then(() => {
	routerReady.value = true
})
</script>
