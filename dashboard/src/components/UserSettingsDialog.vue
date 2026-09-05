<script setup lang="ts">
import {
	Avatar,
	Button,
	ErrorMessage,
	FormControl,
	SettingsBody,
	SettingsContent,
	SettingsDialog,
	SettingsHeader,
	SettingsNavGroup,
	SettingsNavItem,
	SettingsPanel,
	SettingsSidebar,
	Textarea,
	toast,
	useDoc,
	useKeyboardShortcut,
} from "frappe-ui"
import { computed, reactive, ref, watch } from "vue"

import AvatarUploader from "@/components/common/AvatarUploader.vue"
import TeamsPanel from "@/components/dashboard/teams/TeamsPanel.vue"
import { session } from "@/data/session"
import { reloadTeams } from "@/data/teams"
import { userResource } from "@/data/user"

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
	if (!isOpen) return
	Object.assign(form, savedProfile())
	// Memberships change under the cached list, so the teams tab reads a fresh one.
	reloadTeams()
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
	<SettingsDialog v-model:open="open" v-model:tab="tab" size="6xl" :shortcut="false">
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

			<SettingsNavGroup :label="__('Team Management')">
				<SettingsNavItem value="teams">
					<template #prefix>
						<span class="lucide-users size-4" />
					</template>
					{{ __("Teams") }}
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
						<AvatarUploader
							v-model="form.user_image"
							:label="fullName"
							:title="__('Profile picture')"
							:description="__('Helps people recognise you')"
						/>

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

			<SettingsPanel value="teams">
				<TeamsPanel />
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
