<script setup lang="ts">
import { createAndSelectTeam, createTeam } from "@/data/teams";
import type { FrappeError } from "@/types";
import { Avatar, Button, Dialog, ErrorMessage, FileUploader, toast } from "frappe-ui";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";

const IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp", "image/svg+xml"];

const router = useRouter();

const isOpen = defineModel<boolean>({ required: true });

const teamName = ref("");
const logo = ref("");
const showErrors = ref(false);

// createResource types its error as {}, so the message needs narrowing.
const errorMessage = computed(() => (createTeam.error as FrappeError | null)?.message);

watch(isOpen, (open) => {
	if (!open) return;
	teamName.value = "";
	logo.value = "";
	showErrors.value = false;
	createTeam.error = null;
});

// The slug and the Owner membership come from the server, so a name is the whole form.
const invalid = computed(() => !teamName.value.trim());

async function submit() {
	showErrors.value = true;
	if (invalid.value) return;

	const team = await createAndSelectTeam({
		team_name: teamName.value.trim(),
		logo: logo.value || null,
	});
	if (!team) return;

	toast.success(`${team.team_name} created`);
	isOpen.value = false;
	// The new team is already the selected one, so the overview opens on it.
	router.push({ name: "team-overview" });
}
</script>

<template>
	<Dialog v-model="isOpen">
		<template #body-title>
			<div class="flex items-center gap-2">
				<span class="lucide-users-round size-5 text-ink-gray-7" />
				<h3 class="text-2xl font-semibold text-ink-gray-9">Create team</h3>
			</div>
		</template>

		<template #body-content>
			<form novalidate class="flex flex-col items-center gap-4" @submit.prevent="submit">
				<FileUploader
					:file-types="IMAGE_TYPES"
					@success="(file: { file_url: string }) => (logo = file.file_url)"
				>
					<template #default="{ openFileSelector, uploading, error: uploadError }">
						<div class="flex flex-col items-center gap-1">
							<!-- The overlay is the control; the avatar under it is only the preview. -->
							<button
								type="button"
								class="group relative rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
								:aria-label="logo ? 'Change logo' : 'Add logo'"
								@click="openFileSelector"
							>
								<!-- Avatar sizes itself from the utility class rather than its size enum,
									 which tops out well below a preview worth looking at. -->
								<Avatar
									:image="logo || undefined"
									shape="square"
									class="size-24 rounded-xl"
								/>
								<!-- Empty, the icon is the whole placeholder; over an uploaded logo it
									 needs the backdrop to stay legible. -->
								<span
									class="absolute inset-0 grid place-items-center rounded-xl transition duration-150"
									:class="[
										logo
											? 'bg-black/50 opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100'
											: 'group-hover:bg-black/50',
										uploading && 'opacity-100',
									]"
								>
									<span
										class="size-6"
										:class="[
											uploading
												? 'lucide-loader-circle animate-spin'
												: 'lucide-camera',
											logo
												? 'text-white'
												: 'text-ink-gray-4 group-hover:text-white',
										]"
									/>
								</span>
							</button>
							<ErrorMessage v-if="uploadError" :message="String(uploadError)" />
						</div>
					</template>
				</FileUploader>

				<!-- Unadorned on purpose: the name reads as the team's title, not as a form field. -->
				<input
					v-model="teamName"
					aria-label="Team name"
					placeholder="Team name"
					autocomplete="off"
					class="w-full bg-transparent text-center text-lg font-medium text-ink-gray-9 placeholder-ink-gray-4 focus:outline-none"
				/>

				<p v-if="showErrors && invalid" class="text-sm text-ink-red-4">
					A team needs a name.
				</p>
				<ErrorMessage v-else :message="errorMessage" />

				<!-- type=button: inside a form, a submit button would run `submit` twice —
					 once on click, once on the form's own submit — and the second insert
					 creates a second team. -->
				<Button
					type="button"
					variant="solid"
					label="Create"
					class="w-full"
					:loading="createTeam.loading"
					@click="submit"
				/>
			</form>
		</template>
	</Dialog>
</template>
