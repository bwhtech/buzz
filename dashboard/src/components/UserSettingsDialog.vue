<script setup lang="ts">
import {
	Avatar,
	Button,
	ErrorMessage,
	FileUploader,
	FormControl,
	SettingsBody,
	SettingsContent,
	SettingsDialog,
	SettingsHeader,
	SettingsNavGroup,
	SettingsNavItem,
	SettingsPanel,
	SettingsSidebar,
	Spinner,
	Textarea,
	toast,
	useDoc,
	useKeyboardShortcut,
} from "frappe-ui"
import { computed, reactive, ref, watch } from "vue"

import { session } from "@/data/session"
import { userResource } from "@/data/user"
import { validateIsImageFile } from "@/utils"

interface UserDoc {
	name: string
	first_name: string
	last_name: string
	user_image: string | null
	bio: string
}

type Profile = Omit<UserDoc, "name">

const open = defineModel<boolean>("open", { default: false })

const tab = ref("profile")

// G then S. useKeyboardShortcut matches one chord at a time, so a sequence is
// two registrations and the window between them.
const SEQUENCE_WINDOW = 1000
let sequenceStartedAt = 0

useKeyboardShortcut({
	combo: "G",
	description: "Start a go-to sequence",
	group: "Navigation",
	preventDefault: false,
	handler: () => {
		sequenceStartedAt = Date.now()
	},
})

useKeyboardShortcut({
	combo: "S",
	description: "Go to settings",
	group: "Navigation",
	preventDefault: false,
	handler: () => {
		if (Date.now() - sequenceStartedAt > SEQUENCE_WINDOW) return

		sequenceStartedAt = 0
		open.value = true
	},
})

// immediate: false — userResource already has the fields; only setValue's PUT is needed.
const user = useDoc<UserDoc>({ doctype: "User", name: session.user, immediate: false })

const form = reactive<Profile>(savedProfile())

// Mounted for the session, so a cancelled edit is discarded on the way back in.
watch(open, (isOpen) => {
	if (isOpen) Object.assign(form, savedProfile())
})

function savedProfile(): Profile {
	const info = userResource.data
	return {
		first_name: info?.first_name ?? "",
		last_name: info?.last_name ?? "",
		user_image: info?.user_image ?? null,
		bio: info?.bio ?? "",
	}
}

const isDirty = computed(() => {
	const saved = savedProfile()
	return (Object.keys(saved) as (keyof Profile)[]).some((field) => form[field] !== saved[field])
})

const fullName = computed(() => [form.first_name, form.last_name].filter(Boolean).join(" "))

async function save() {
	// Resolves null on failure rather than throwing; setValue.error renders inline.
	if (!(await user.setValue.submit({ ...form }))) return

	// full_name is derived server-side.
	await userResource.reload()
	toast.success(__("Profile updated"))
}
</script>

<template>
	<SettingsDialog v-model:open="open" v-model:tab="tab" size="5xl" :shortcut="false">
		<template #title>{{ __("Settings") }}</template>

		<SettingsSidebar>
			<!-- Visible twin of the dialog's sr-only title. -->
			<h2 aria-hidden="true" class="px-2 py-1 text-lg-semibold text-ink-gray-8">
				{{ __("Settings") }}
			</h2>

			<SettingsNavGroup :label="__('Account')">
				<SettingsNavItem value="profile">
					<template #prefix>
						<Avatar size="xs" :image="form.user_image ?? undefined" :label="fullName" />
					</template>
					{{ __("Profile") }}
				</SettingsNavItem>
			</SettingsNavGroup>
		</SettingsSidebar>

		<SettingsContent>
			<SettingsPanel value="profile">
				<SettingsHeader :title="__('Profile')" :description="__('How you appear across Buzz.')">
					<template #actions>
						<Transition name="save">
							<Button
								v-if="isDirty || user.setValue.loading"
								variant="solid"
								:loading="user.setValue.loading"
								@click="save"
							>
								{{ __("Save") }}
							</Button>
						</Transition>
					</template>
				</SettingsHeader>

				<SettingsBody>
					<div class="flex flex-col gap-6 pt-6">
						<FileUploader
							:validate-file="validateIsImageFile"
							file-types="image/*"
							@success="(file: { file_url: string }) => (form.user_image = file.file_url)"
						>
							<template #default="{ openFileSelector, error: uploadError, uploading }">
								<div class="flex items-center gap-4">
									<button
										type="button"
										class="group relative size-16 shrink-0 overflow-hidden rounded-full bg-surface-gray-3 transition-transform duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] focus-visible:outline-none focus-visible:focus-ring active:scale-[0.97] motion-reduce:transition-none motion-reduce:active:scale-100"
										:aria-label="form.user_image ? __('Change photo') : __('Upload photo')"
										@click="openFileSelector"
									>
										<img
											v-if="form.user_image"
											:src="form.user_image"
											:alt="fullName"
											class="size-full object-cover"
										/>
										<!-- Over an image the scrim is a hover affordance; over the empty
										     circle the camera is the only click cue. -->
										<span
											class="absolute inset-0 flex items-center justify-center transition-opacity duration-150 ease-[cubic-bezier(0.23,1,0.32,1)]"
											:class="
												form.user_image
													? 'bg-black/40 opacity-0 group-hover:opacity-100 group-focus-visible:opacity-100'
													: ''
											"
										>
											<Spinner
												v-if="uploading"
												class="size-5"
												:class="form.user_image ? 'text-white' : 'text-ink-gray-5'"
											/>
											<span
												v-else
												class="lucide-camera size-5"
												:class="form.user_image ? 'text-white' : 'text-ink-gray-5'"
											/>
										</span>
									</button>

									<div class="flex flex-col gap-1">
										<span class="text-base-medium text-ink-gray-8">
											{{ __("Profile picture") }}
										</span>
										<p class="text-p-sm text-ink-gray-5">
											{{ __("Helps people recognise you") }}
										</p>
										<button
											v-if="form.user_image"
											type="button"
											class="self-start text-p-sm text-ink-gray-6 underline underline-offset-2 transition-colors duration-150 hover:text-ink-gray-8"
											@click="form.user_image = null"
										>
											{{ __("Remove") }}
										</button>
										<ErrorMessage :message="(uploadError as string) ?? ''" />
									</div>
								</div>
							</template>
						</FileUploader>

						<div class="grid gap-4 sm:grid-cols-2">
							<FormControl type="text" :label="__('First Name')" v-model="form.first_name" />
							<FormControl type="text" :label="__('Last Name')" v-model="form.last_name" />
						</div>

						<Textarea :label="__('Bio')" :rows="3" maxlength="280" v-model="form.bio" />

						<FormControl
							type="email"
							:label="__('Email')"
							:model-value="userResource.data?.email"
							disabled
						/>

						<ErrorMessage :message="user.setValue.error?.message" />
					</div>
				</SettingsBody>
			</SettingsPanel>
		</SettingsContent>
	</SettingsDialog>
</template>

<style scoped>
/* Leave is quicker than enter: the user has already decided by then. */
.save-enter-active {
	transition:
		opacity 150ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 150ms cubic-bezier(0.23, 1, 0.32, 1);
}

.save-leave-active {
	transition:
		opacity 100ms cubic-bezier(0.23, 1, 0.32, 1),
		transform 100ms cubic-bezier(0.23, 1, 0.32, 1);
}

.save-enter-from,
.save-leave-to {
	opacity: 0;
	transform: scale(0.95);
}

/* Reduced motion keeps the fade, drops the movement. */
@media (prefers-reduced-motion: reduce) {
	.save-enter-from,
	.save-leave-to {
		transform: none;
	}
}
</style>
