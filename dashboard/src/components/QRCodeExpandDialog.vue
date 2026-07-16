<template>
	<Dialog v-model="isOpen" :options="{ title: __('QR Code'), size: 'lg' }">
		<template #body-content>
			<div class="flex justify-center">
				<img :src="qrCodeSrc" :alt="altText" class="w-full max-w-sm" />
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog } from "frappe-ui";

const isOpen = defineModel({ type: Boolean, default: false });

defineProps({
	qrCodeSrc: {
		type: String,
		required: true,
	},
	altText: {
		type: String,
		default: "QR Code",
	},
});
</script>
