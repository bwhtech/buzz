<template>
	<div class="max-w-2xl mx-auto py-8 px-4">
		<div class="w-8 mx-auto" v-if="campaignResource.loading">
			<Spinner />
		</div>

		<div v-else-if="registered" class="text-center">
			<div class="bg-surface-green-1 border border-outline-green-1 rounded-lg p-8">
				<LucideCheckCircle class="w-16 h-16 text-ink-green-2 mx-auto mb-4" />
				<h2 class="text-ink-green-3 font-semibold text-xl mb-2">
					{{ __("Thank you for your interest!") }}
				</h2>
				<p class="text-ink-green-2">
					{{ __("We have registered your interest and will be in touch soon.") }}
				</p>
			</div>
		</div>

		<div
			v-else-if="campaign"
			class="bg-surface-white border border-outline-gray-1 rounded-lg p-6"
		>
			<h1 class="text-ink-gray-9 font-bold text-2xl mb-6">
				{{ campaign.title }}
			</h1>

			<div
				class="prose prose-sm max-w-none mb-8 text-ink-gray-7"
				v-html="renderedDescription"
			></div>

			<Button
				variant="solid"
				size="lg"
				class="w-full"
				:loading="registerResource.loading"
				@click="registerInterest"
			>
				{{ __("Register") }}
			</Button>

			<p v-if="errorMessage" class="text-ink-red-2 text-sm mt-4 text-center">
				{{ errorMessage }}
			</p>
		</div>

		<div v-else-if="error" class="text-center">
			<div class="bg-surface-red-1 border border-outline-red-1 rounded-lg p-8">
				<LucideXCircle class="w-16 h-16 text-ink-red-2 mx-auto mb-4" />
				<h2 class="text-ink-red-3 font-semibold text-xl mb-2">
					{{ __("Campaign Not Found") }}
				</h2>
				<p class="text-ink-red-2">
					{{ error }}
				</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { FrappeError } from "@/types";
import { Button, Spinner, createResource } from "frappe-ui";
import { marked } from "marked";
import { computed, ref } from "vue";
import LucideCheckCircle from "~icons/lucide/check-circle";
import LucideXCircle from "~icons/lucide/x-circle";

interface Campaign {
	title?: string;
	description?: string;
	[key: string]: any;
}

const props = defineProps({
	campaign: {
		type: String,
		required: true,
	},
});

const campaign = ref<Campaign | null>(null);
const registered = ref(false);
const error = ref<string | null>(null);
const errorMessage = ref<string | null>(null);

const renderedDescription = computed(() => {
	if (!campaign.value?.description) return "";
	return marked(campaign.value.description);
});

const campaignResource = createResource({
	url: "buzz.api.get_campaign_details",
	params: {
		campaign: props.campaign,
	},
	auto: true,
	onSuccess: (data: Campaign) => {
		campaign.value = data;
	},
	onError: (err: FrappeError) => {
		error.value = err.messages?.[0] || __("Campaign not found or not active");
	},
});

const registerResource = createResource({
	url: "buzz.api.register_campaign_interest",
	onSuccess: () => {
		registered.value = true;
		errorMessage.value = null;
	},
	onError: (err: FrappeError) => {
		errorMessage.value = err.messages?.[0] || __("Failed to register interest");
	},
});

function registerInterest() {
	registerResource.submit({
		campaign: props.campaign,
	});
}
</script>
