<template>
	<div v-if="profile" class="flex w-full items-center justify-between mb-3 sm:mb-5">
		<FileUploader
			@success="(file: { file_url: string }) => updateImage(file.file_url)"
			:validateFile="validateIsImageFile"
		>
			<template #default="{ openFileSelector, error: _error }">
				<div class="flex items-center gap-4">
					<div class="group relative !size-[66px]">
						<Avatar
							class="!size-16"
							:image="profile.user_image"
							:label="profile.full_name"
						/>
						<component
							:is="profile.user_image ? Dropdown : 'div'"
							v-bind="
								profile.user_image
									? {
											options: [
												{
													icon: 'upload',
													label: profile.user_image
														? __('Change image')
														: __('Upload image'),
													onClick: openFileSelector,
												},
												{
													icon: 'trash-2',
													label: __('Remove image'),
													onClick: () => updateImage(),
												},
											],
									  }
									: { onClick: openFileSelector }
							"
							class="!absolute bottom-0 left-0 right-0"
						>
							<div
								class="z-1 absolute bottom-0.5 left-0 right-0.5 flex h-9 cursor-pointer items-center justify-center rounded-b-full bg-black bg-opacity-40 pt-3 opacity-0 duration-300 ease-in-out group-hover:opacity-100"
								style="
									-webkit-clip-path: inset(12px 0 0 0);
									clip-path: inset(12px 0 0 0);
								"
							>
								<LucideCamera class="size-4 cursor-pointer text-white" />
							</div>
						</component>
					</div>
					<div class="flex flex-col gap-1">
						<span class="text-2xl font-semibold text-ink-gray-8">
							{{ profile.full_name }}
						</span>
						<span class="text-base text-ink-gray-7">
							{{ profile.email }}
						</span>
						<ErrorMessage :message="__(_error as string)" />
					</div>
				</div>
			</template>
		</FileUploader>
	</div>
</template>

<script setup lang="ts">
import type { FrappeError } from "@/types";
import { validateIsImageFile } from "@/utils";
import { Avatar, Dropdown, FileUploader, createResource, toast } from "frappe-ui";
import { onMounted, ref } from "vue";
import LucideCamera from "~icons/lucide/camera";
import { userResource } from "../data/user";

interface UserProfile {
	name?: string;
	full_name?: string;
	email?: string;
	user_image?: string;
	first_name?: string;
	last_name?: string;
}

const user = (userResource.data || {}) as UserProfile;

const profile = ref<UserProfile>({});
const error = ref("");

const setUser = createResource({
	url: "frappe.client.set_value",
	makeParams() {
		return {
			doctype: "User",
			name: user.name,
			fieldname: {
				first_name: profile.value.first_name,
				last_name: profile.value.last_name,
				user_image: profile.value.user_image,
			},
		};
	},
	onSuccess: () => {
		error.value = "";
		toast.success(__("Profile updated successfully"));
	},
	onError: (err: FrappeError) => {
		error.value = err.messages?.[0] || __("Failed to update profile");
	},
});

function updateImage(fileUrl = "") {
	profile.value.user_image = fileUrl;
	setUser.submit();
}

onMounted(() => {
	profile.value = { ...userResource.data };
});
</script>
