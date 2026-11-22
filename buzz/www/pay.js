// The buzz.events pay page: opens the gateway's dialog or redirect, then waits for the payment.
const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds))

{
	const config = JSON.parse(document.getElementById("checkout-config").textContent)
	const API = "/api/v2/method/buzz.api.hosted_payments"
	const SETTLED_STATUSES = ["Paid", "Partially Refunded", "Refunded"]
	const POLL_INTERVAL_MS = 2000
	const POLL_ATTEMPTS = 15
	const openedKey = `buzz-pay-opened:${config.order_id}`
	const page = document.querySelector(".pay")
	const processingTitle = document.getElementById("pay-processing-title")
	const retryButton = document.getElementById("pay-retry")
	let dialog = null

	function rememberOpened() {
		try {
			sessionStorage.setItem(openedKey, "1")
		} catch {
			// Storage is blocked: the page then opens the checkout again when the buyer comes back.
		}
	}

	function wasOpened() {
		try {
			return sessionStorage.getItem(openedKey) === "1"
		} catch {
			return false
		}
	}

	function backToSite() {
		window.location.replace(config.return_url)
	}

	function showProcessing(title) {
		if (title) processingTitle.textContent = title
		page.dataset.state = "processing"
	}

	function showNotCompleted(status) {
		retryButton.hidden = Boolean(status) && status !== "Pending"
		page.dataset.state = "failed"
	}

	async function readStatus() {
		const query = new URLSearchParams({ order_id: config.order_id })
		const response = await fetch(`${API}.get_checkout_status?${query}`, {
			headers: { Accept: "application/json" },
		})
		return response.ok ? (await response.json()).data : null
	}

	async function waitForPayment(title, attempts = POLL_ATTEMPTS) {
		showProcessing(title)
		let status = null
		for (let attempt = 1; attempt <= attempts; attempt++) {
			status = await readStatus().catch(() => null)
			if (SETTLED_STATUSES.includes(status)) return backToSite()
			if ((status && status !== "Pending") || attempt === attempts) break
			await sleep(POLL_INTERVAL_MS)
		}
		showNotCompleted(status)
	}

	// Closing the dialog means the buyer chose not to pay, so one check is enough.
	function checkDismissedPayment() {
		return waitForPayment(undefined, 1)
	}

	async function confirmPayment(result) {
		showProcessing("Processing your payment")
		const response = await fetch(`${API}.confirm_checkout`, {
			method: "POST",
			headers: {
				Accept: "application/json",
				"Content-Type": "application/json",
				"X-Frappe-CSRF-Token": window.frappe?.csrf_token || "",
			},
			body: JSON.stringify({ order_id: config.order_id, payload: result }),
		}).catch(() => null)
		const status = response?.ok ? (await response.json()).data : null
		if (SETTLED_STATUSES.includes(status)) return backToSite()
		waitForPayment()
	}

	function loadScript(url) {
		return new Promise((resolve, reject) => {
			const script = document.createElement("script")
			script.src = url
			script.addEventListener("load", resolve)
			script.addEventListener("error", reject)
			document.head.append(script)
		})
	}

	async function openDialog() {
		if (!dialog) {
			await loadScript(config.checkout.script_url)
			dialog = new window.Razorpay({
				...config.checkout.options,
				handler: confirmPayment,
				modal: { ondismiss: checkDismissedPayment },
			})
		}
		dialog.open()
	}

	function openCheckout() {
		rememberOpened()
		showProcessing()
		if (config.redirect_url) return window.location.assign(config.redirect_url)
		if (!config.checkout) return showNotCompleted()
		openDialog().catch(() => showNotCompleted())
	}

	retryButton.addEventListener("click", openCheckout)

	if (SETTLED_STATUSES.includes(config.status)) backToSite()
	else if (config.status !== "Pending") showNotCompleted(config.status)
	else if (wasOpened()) waitForPayment()
	else openCheckout()
}
