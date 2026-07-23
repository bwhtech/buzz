<template>
	<div class="min-h-screen bg-surface-base text-ink-gray-8">
		<div>
			<Navbar />
		</div>
		<div class="max-w-4xl py-8 px-4 md:py-12 mx-auto">
			<template v-if="!routerReady">
				<div class="flex justify-center py-16">
					<Spinner class="w-8 h-8" />
				</div>
			</template>
			<template v-else-if="requires_auth && !session.isLoggedIn">
				<LoginRequired />
			</template>
			<template v-else>
				<slot></slot>
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
import LoginRequired from "@/components/LoginRequired.vue";
import Navbar from "@/components/Navbar.vue";
import { session } from "@/data/session";
import { Spinner } from "frappe-ui";
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();
const routerReady = ref(false);
const requires_auth = computed(() => !route.meta?.isPublic);

router.isReady().then(() => {
	routerReady.value = true;
});
</script>
