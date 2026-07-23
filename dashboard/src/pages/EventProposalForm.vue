<template>
	<div>
		<div class="w-8 mx-auto" v-if="form_data_resource.loading">
			<Spinner />
		</div>

		<div v-else-if="submitted" class="text-center">
			<div class="bg-surface-green-1 border border-outline-green-1 rounded-lg p-8">
				<LucideCheckCircle class="w-16 h-16 text-ink-green-6 mx-auto mb-4" />
				<h2 class="text-ink-green-6 text-2xl-semibold mb-2">
					{{ form_data?.success_title }}
				</h2>
				<div
					v-if="rendered_success_message"
					class="prose prose-sm max-w-none text-ink-green-6"
					v-html="rendered_success_message"
				></div>
				<p v-else class="text-ink-green-6">
					{{ __("Your proposal has been received.") }}
				</p>
			</div>
		</div>

		<LoginRequired
			v-else-if="login_required"
			:message="__('Please log in to submit a proposal.')"
		/>

		<div v-else-if="form_data">
			<form
				class="bg-surface-base border border-outline-gray-1 rounded-lg"
				@submit.prevent="handleSubmit"
			>
				<div class="px-6 py-5 border-b border-outline-gray-1">
					<h1 class="text-ink-gray-9 text-3xl-bold">
						{{ form_data.banner_title }}
					</h1>
				</div>

				<div class="p-6">
					<FormFieldSections :fields="form_data.form_fields">
						<template #field="{ field }">
							<CustomFieldInput
								:field="{ ...field, mandatory: field.reqd }"
								:model-value="form_values[field.fieldname]"
								@update:model-value="form_values[field.fieldname] = $event"
							/>
						</template>
					</FormFieldSections>
				</div>

				<div class="px-6 pb-6">
					<Button
						variant="solid"
						size="lg"
						class="w-full"
						:loading="submit_resource.loading"
						type="submit"
					>
						{{ __("Submit") }}
					</Button>
				</div>
			</form>
		</div>

		<div v-else-if="load_error" class="text-center">
			<div class="bg-surface-amber-1 border border-outline-amber-1 rounded-lg p-8">
				<LucideAlertCircle class="w-16 h-16 text-ink-amber-6 mx-auto mb-4" />
				<h2 class="text-ink-amber-6 text-2xl-semibold mb-2">
					{{ __("Not Found") }}
				</h2>
				<p class="text-ink-amber-5">
					{{ load_error }}
				</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import CustomFieldInput from "@/components/CustomFieldInput.vue";
import FormFieldSections from "@/components/FormFieldSections.vue";
import LoginRequired from "@/components/LoginRequired.vue";
import type { FrappeError, FrappeField } from "@/types";
import { Button, Spinner, createResource, toast } from "frappe-ui";
import { marked } from "marked";
import { computed, reactive, ref } from "vue";
import LucideAlertCircle from "~icons/lucide/alert-circle";
import LucideCheckCircle from "~icons/lucide/check-circle";

interface ProposalFormData {
	success_message?: string;
	banner_title?: string;
	form_fields?: FrappeField[];
	[key: string]: any;
}

const form_data = ref<ProposalFormData | null>(null);
const form_values = reactive<Record<string, any>>({});
const submitted = ref(false);
const login_required = ref(false);
const load_error = ref<string | null>(null);

const rendered_success_message = computed(() => {
	const msg = form_data.value?.success_message;
	if (!msg) return "";
	return marked(msg);
});

const form_data_resource = createResource({
	url: "buzz.api.forms.get_event_proposal_form_data",
	auto: true,
	onSuccess: (data: ProposalFormData) => {
		form_data.value = data;
		for (const field of data.form_fields || []) {
			if (field.default) {
				form_values[field.fieldname] = field.default;
			}
		}
	},
	onError: (err: FrappeError) => {
		if (err.exc_type === "AuthenticationError") {
			login_required.value = true;
			return;
		}
		load_error.value = err.messages?.[0] || __("Form not found");
	},
});

const submit_resource = createResource({
	url: "buzz.api.forms.submit_event_proposal",
	onSuccess: () => {
		submitted.value = true;
	},
	onError: (err: FrappeError) => {
		const messages = err.messages || [];
		const msg = messages.find((m) => typeof m === "string" && m.trim());
		toast.error(msg || __("Failed to submit proposal"));
	},
});

function handleSubmit() {
	submit_resource.submit({ data: { ...form_values } });
}
</script>
