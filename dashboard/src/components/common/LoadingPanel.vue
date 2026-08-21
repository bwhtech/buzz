<script setup lang="ts">
import BuzzLogo from "@/components/common/BuzzLogo.vue";

withDefaults(defineProps<{ text?: string }>(), { text: "Loading" });
</script>

<template>
	<div class="flex h-full min-h-64 flex-col items-center justify-center gap-4">
		<div class="relative">
			<!-- The copy behind carries the ping, so the logo itself stays readable. -->
			<BuzzLogo
				aria-hidden="true"
				class="absolute inset-0 w-9 h-7 animate-ping text-ink-gray-3 motion-reduce:hidden"
			/>
			<BuzzLogo class="relative w-9 h-7 text-ink-gray-4" />
		</div>
		<p class="text-sm text-ink-gray-5">{{ text }}</p>
	</div>
</template>
