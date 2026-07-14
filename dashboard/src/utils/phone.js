// Pure, framework-free phone parse/format helpers used by PhoneInput.vue.
// No Vue imports so it stays unit-testable with node --test.
// Canonical format matches Frappe's Phone control: "<dialCode>-<digits>".

export const DEFAULT_DIAL_CODE = "+1";

// Returns the leading dial code of `str` (e.g. "+91"), or null.
// Prefers the longest matching code from knownDialCodes; falls back to
// "+" followed by 1-4 digits when the list has not loaded yet.
function matchLeadingDialCode(str, knownDialCodes) {
	if (!str.startsWith("+")) return null;
	const sorted = [...knownDialCodes].sort((first, second) => second.length - first.length);
	for (const code of sorted) {
		if (str.startsWith(code)) return code;
	}
	const fallback = str.match(/^\+\d{1,4}/);
	return fallback ? fallback[0] : null;
}

// Splits a stored phone value into its dial code and a digits-only local number.
// Strips ALL leading dial codes so a doubled value ("+91 +91 ...") is healed,
// and tolerates both hyphen and space separators.
export function parsePhone(value, knownDialCodes = []) {
	const raw = String(value ?? "").trim();
	if (!raw) return { dialCode: null, localNumber: "" };

	let dialCode = null;
	let rest = raw;
	let code = matchLeadingDialCode(rest, knownDialCodes);
	while (code) {
		if (dialCode === null) dialCode = code;
		rest = rest.slice(code.length).replace(/^[\s-]+/, "");
		code = matchLeadingDialCode(rest, knownDialCodes);
	}

	return { dialCode, localNumber: rest.replace(/\D/g, "") };
}

// Joins a dial code and local number into Frappe's canonical hyphen format.
export function formatPhone(dialCode, localNumber) {
	const digits = String(localNumber ?? "").replace(/\D/g, "");
	if (!digits) return "";
	return `${dialCode}-${digits}`;
}
