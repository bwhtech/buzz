// Currency formatting utilities using JavaScript Intl API

export function formatCurrency(
	amount: number | undefined,
	currencyCode = "INR",
	locale = "en-US",
	options: Intl.NumberFormatOptions = {},
) {
	amount = amount ?? 0
	try {
		return new Intl.NumberFormat(locale, {
			style: "currency",
			currency: currencyCode,
			...options,
		}).format(amount)
	} catch {
		// Fallback if currency code is invalid or not supported
		console.warn(`Invalid currency code: ${currencyCode}. Falling back to default formatting.`)
		return new Intl.NumberFormat(locale, {
			style: "currency",
			currency: "INR",
		}).format(amount)
	}
}

export function formatPrice(price: number, currencyCode = "INR", locale = "en-US") {
	return formatCurrency(price, currencyCode, locale)
}

export function formatPriceOrFree(price?: number, currencyCode = "INR", locale = "en-US") {
	if (!price || !Number.isFinite(price)) {
		return __("Free")
	}
	return formatPrice(price, currencyCode, locale)
}

// Whole amounts drop the ".00"; fractional ones keep the currency's own decimals.
export function formatWholePriceOrFree(price?: number, currencyCode = "INR", locale = "en-US") {
	if (!price || !Number.isFinite(price)) {
		return __("Free")
	}
	const options = Number.isInteger(price)
		? { minimumFractionDigits: 0, maximumFractionDigits: 0 }
		: {}
	return formatCurrency(price, currencyCode, locale, options)
}

export function getCurrencySymbol(currencyCode: string, locale = "en-US") {
	try {
		const formatter = new Intl.NumberFormat(locale, {
			style: "currency",
			currency: currencyCode,
			minimumFractionDigits: 0,
			maximumFractionDigits: 0,
		})

		// Format a small number and extract just the symbol
		const formatted = formatter.format(0)
		return formatted.replace(/[\d\s,]/g, "").trim()
	} catch {
		console.warn(`Invalid currency code: ${currencyCode}`)
		return currencyCode
	}
}

type NumberFormatSeparators = { decimalSeparator: string; groupSeparator: string }

// Frappe's Currency.number_format choices, mirroring frappe's number_format.js.
const NUMBER_FORMATS: Record<string, NumberFormatSeparators> = {
	"#,###.##": { decimalSeparator: ".", groupSeparator: "," },
	"#.###,##": { decimalSeparator: ",", groupSeparator: "." },
	"# ###.##": { decimalSeparator: ".", groupSeparator: " " },
	"# ###,##": { decimalSeparator: ",", groupSeparator: " " },
	"#'###.##": { decimalSeparator: ".", groupSeparator: "'" },
	"#, ###.##": { decimalSeparator: ".", groupSeparator: ", " },
	"#,##,###.##": { decimalSeparator: ".", groupSeparator: "," },
	"#,###.###": { decimalSeparator: ".", groupSeparator: "," },
	"#.###": { decimalSeparator: "", groupSeparator: "." },
	"#,###": { decimalSeparator: "", groupSeparator: "," },
}
const DEFAULT_NUMBER_FORMAT = "#,###.##"

export function numberFormatSeparators(numberFormat?: string | null): NumberFormatSeparators {
	return NUMBER_FORMATS[numberFormat ?? ""] ?? NUMBER_FORMATS[DEFAULT_NUMBER_FORMAT]
}

// Whole amounts drop the decimals, as formatWholePriceOrFree does.
export function formatNumber(value: number, numberFormat?: string | null) {
	const format = numberFormat && NUMBER_FORMATS[numberFormat] ? numberFormat : DEFAULT_NUMBER_FORMAT
	const { decimalSeparator, groupSeparator } = NUMBER_FORMATS[format]
	const decimalPlaces = decimalSeparator ? (format.split(decimalSeparator)[1]?.length ?? 0) : 0
	const [wholeDigits, fractionDigits = ""] = Math.abs(value).toFixed(decimalPlaces).split(".")
	// Indian grouping puts a separator after the last three digits, then every two.
	const groupPattern = format === "#,##,###.##" ? /(\d)(?=(\d\d)+\d$)/g : /(\d)(?=(\d{3})+$)/g
	const groupedWhole = wholeDigits.replace(groupPattern, `$1${groupSeparator}`)
	const fraction = /^0*$/.test(fractionDigits) ? "" : decimalSeparator + fractionDigits
	return `${value < 0 ? "-" : ""}${groupedWhole}${fraction}`
}

// Reads a typed amount back, honouring the format's decimal separator.
export function parseNumber(text: string, numberFormat?: string | null) {
	const { decimalSeparator } = numberFormatSeparators(numberFormat)
	const strayCharacters = { ",": /[^\d,]/g, ".": /[^\d.]/g }[decimalSeparator] ?? /\D/g
	const parsed = Number.parseFloat(text.replace(strayCharacters, "").replace(",", "."))
	return Number.isFinite(parsed) ? parsed : 0
}
