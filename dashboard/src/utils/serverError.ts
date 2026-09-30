/**
 * What the server said, without the exception type frappe-ui puts in front of it
 * ("ValidationError: Coupon expired"). Anything not shaped "type: message" is returned
 * as it is.
 */
export function serverErrorMessage(error: unknown): string {
	const { message = "", type } = (error ?? {}) as { message?: string; type?: string }
	const prefix = `${type}: `
	return type && message.startsWith(prefix) ? message.slice(prefix.length) : message
}
