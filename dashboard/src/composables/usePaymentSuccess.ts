import { type Ref, onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"

import { triggerCelebrationConfetti } from "@/utils/confetti"

interface PaymentSuccessOptions {
	onSuccess?: () => void
	messageDuration?: number
	enableConfetti?: boolean
	cleanupUrl?: boolean
}

interface PaymentSuccessReturn {
	showSuccessMessage: Ref<boolean>
	triggerSuccessFlow: () => void
	checkForSuccess: () => void
	hideSuccessMessage: () => void
	showSuccess: () => void
}

/**
 * Composable for handling payment success flow
 * Handles success message display, confetti animation, URL cleanup, and data refresh
 *
 * @param {Object} options - Configuration options
 * @param {Function} options.onSuccess - Callback function to execute on success (e.g., reload data)
 * @param {number} options.messageDuration - How long to show success message in milliseconds (default: 10000)
 * @param {boolean} options.enableConfetti - Whether to trigger confetti animation (default: true)
 * @param {boolean} options.cleanupUrl - Whether to clean up success parameter from URL (default: true)
 * @returns {Object} - Returns reactive state and helper functions
 */
export function usePaymentSuccess(options: PaymentSuccessOptions = {}): PaymentSuccessReturn {
	const { onSuccess, messageDuration = 10000, enableConfetti = true, cleanupUrl = true } = options

	const route = useRoute()
	const router = useRouter()

	const showSuccessMessage = ref(false)

	/**
	 * Trigger the complete success flow
	 */
	const triggerSuccessFlow = () => {
		// Show success message
		showSuccessMessage.value = true

		// Trigger confetti animation
		if (enableConfetti) {
			triggerCelebrationConfetti()
		}

		// Execute custom success callback (e.g., reload data)
		if (onSuccess && typeof onSuccess === "function") {
			onSuccess()
		}

		// Clean up the URL by removing the success parameter
		if (cleanupUrl) {
			router.replace({
				name: route.name,
				params: route.params,
			})
		}

		// Hide success message after specified duration
		if (messageDuration > 0) {
			setTimeout(() => {
				showSuccessMessage.value = false
			}, messageDuration)
		}
	}

	/**
	 * Check for success parameter and trigger flow if present
	 */
	const checkForSuccess = () => {
		if (route.query.success === "true") {
			triggerSuccessFlow()
		}
	}

	/**
	 * Manually hide the success message
	 */
	const hideSuccessMessage = () => {
		showSuccessMessage.value = false
	}

	/**
	 * Manually show the success message
	 */
	const showSuccess = () => {
		triggerSuccessFlow()
	}

	// Auto-check for success on mount
	onMounted(() => {
		checkForSuccess()
	})

	return {
		showSuccessMessage,
		triggerSuccessFlow,
		checkForSuccess,
		hideSuccessMessage,
		showSuccess,
	}
}
