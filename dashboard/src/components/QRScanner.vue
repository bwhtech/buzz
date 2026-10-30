<template>
	<div class="grid grid-rows-[1fr] [clip-path:circle(75%_at_50%_50%)]">
		<div class="min-h-0 overflow-hidden rounded-7 border border-outline-gray-2">
			<div class="relative mx-auto aspect-square w-full max-w-md bg-surface-gray-2">
				<div
					id="qr-reader"
					class="w-full text-ink-gray-7"
					:class="{ 'opacity-50': isProcessingTicket }"
				></div>

				<Transition
					leave-active-class="transition-opacity duration-200 ease-out motion-reduce:transition-none"
					leave-to-class="opacity-0"
				>
					<div
						v-if="status !== 'ready'"
						class="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-surface-gray-2 p-6 text-center"
						role="status"
					>
						<Icon :icon="statusIcon" class="size-6 text-ink-gray-5" />
						<LoadingText v-if="status !== 'blocked'" :text="statusMessage" />
						<p v-else class="text-p-base text-ink-gray-6">{{ statusMessage }}</p>
					</div>
				</Transition>

				<div
					v-if="isProcessingTicket"
					class="absolute inset-0 flex items-center justify-center bg-surface-elevation-1/75"
				>
					<Spinner class="size-8" />
				</div>
			</div>

			<div class="flex gap-2 border-t border-outline-gray-2 bg-surface-gray-1 p-4">
				<TextInput
					v-model="manualTicketId"
					placeholder="Enter ticket ID manually"
					class="flex-1"
					:disabled="isProcessingTicket"
				/>
				<Button
					:loading="isProcessingTicket"
					:disabled="!manualTicketId.trim()"
					@click="handleManualEntry"
				>
					{{ __("Check") }}
				</Button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button, Icon, LoadingText, Spinner, TextInput, toast } from "frappe-ui"
import { Html5Qrcode } from "html5-qrcode"
import { computed, onMounted, onUnmounted, ref, watch } from "vue"

import { useTicketValidation } from "@/composables/useTicketValidation"
import { extractTicketId } from "@/utils/ticketQr"

// Paused while a scanned guest is open, so the same QR isn't read again behind the dialog.
const props = defineProps<{ paused?: boolean }>()

const { validateTicket, isProcessingTicket } = useTicketValidation()

type CameraStatus = "requesting" | "starting" | "ready" | "blocked"

const status = ref<CameraStatus>("starting")
const manualTicketId = ref("")
const lastScannedTicketId = ref<string | null>(null)
let scanner: Html5Qrcode | null = null
let scanTimeout: ReturnType<typeof setTimeout> | null = null
let unmounted = false
const permissionListener = new AbortController()

const statusMessage = computed(
	() =>
		({
			requesting: __("Allow camera access to scan tickets"),
			starting: __("Starting camera"),
			ready: "",
			blocked: __(
				"Camera unavailable. Allow camera access in your browser settings, or enter the ticket ID below.",
			),
		})[status.value],
)

const statusIcon = computed(() =>
	status.value === "blocked" ? "lucide-camera-off" : "lucide-camera",
)

const watchCameraPermission = () =>
	navigator.permissions
		?.query({ name: "camera" as PermissionName })
		.then((permission) => {
			const sync = () => {
				if (status.value === "ready" || status.value === "blocked") return
				status.value = permission.state === "granted" ? "starting" : "requesting"
			}
			sync()
			permission.addEventListener("change", sync, { signal: permissionListener.signal })
		})
		.catch(() => {})

const startScanner = () => {
	watchCameraPermission()
	scanner = new Html5Qrcode("qr-reader")
	scanner
		.start(
			{ facingMode: "environment" },
			{ fps: 10, qrbox: { width: 250, height: 250 }, aspectRatio: 1.0 },
			onScanSuccess,
			undefined,
		)
		.then(() => (unmounted ? stopScanner() : (status.value = "ready")))
		.catch((error) => {
			console.error("Failed to start scanner:", error)
			status.value = "blocked"
		})
}

const stopScanner = () => {
	if (!scanner?.isScanning) return
	scanner
		.stop()
		.then(() => scanner?.clear())
		.catch((error) => console.error("Failed to stop scanner:", error))
}

watch(
	() => props.paused,
	(paused) => {
		if (status.value !== "ready" || !scanner) return
		if (paused) scanner.pause(true)
		else scanner.resume()
	},
)

const onScanSuccess = (decodedText: string) => {
	const ticketId = extractTicketId(decodedText)
	if (!ticketId) {
		toast.error(__("Invalid QR code format"))
		return
	}

	// Prevent duplicate scans of the same ticket within 2 seconds
	if (lastScannedTicketId.value === ticketId) return

	if (scanTimeout) clearTimeout(scanTimeout)
	lastScannedTicketId.value = ticketId
	validateTicket(ticketId)
	scanTimeout = setTimeout(() => (lastScannedTicketId.value = null), 2000)
}

const handleManualEntry = () => {
	const ticketId = manualTicketId.value.trim()
	if (!ticketId) return

	validateTicket(ticketId)
	manualTicketId.value = ""
}

onMounted(startScanner)

onUnmounted(() => {
	unmounted = true
	permissionListener.abort()
	stopScanner()
	if (scanTimeout) clearTimeout(scanTimeout)
})
</script>

<style scoped>
#qr-reader {
	width: 100%;
}

:global(#qr-reader img[alt="Info icon"]) {
	display: none !important;
}

:global(#qr-reader img[alt="Camera based scan"]) {
	display: none !important;
}

/* Override html5-qrcode styles for better mobile experience */
:global(#qr-reader > div:first-child) {
	border: none !important;
}

:global(#qr-reader video) {
	border-radius: 0 !important;
}

/* Hide duplicate shaded regions - only show the first one */
:global(#qr-shaded-region:not(:first-of-type)) {
	display: none !important;
}

/* Hide the dashboard UI since we're using our own controls */
:global(#qr-reader__dashboard) {
	display: none !important;
}
</style>
