// Buzz Event stores an IANA zone name; these turn one into the two lines the picker
// shows. Everything comes from Intl, so the list tracks the browser's own tzdata.

/**
 * Zones IANA has renamed, which the runtime still reports under the old name.
 *
 * Neither `supportedValuesOf` nor `resolvedOptions` canonicalises, so without this an
 * organiser in India picks a zone labelled "Calcutta". Both spellings resolve to the
 * same zone in Python's `ZoneInfo`, so the rename is safe for what gets stored. Only
 * the renames a reader would notice are listed; the rest of the list passes through.
 */
const RENAMED = {
	"Asia/Calcutta": "Asia/Kolkata",
	"Asia/Katmandu": "Asia/Kathmandu",
	"Asia/Rangoon": "Asia/Yangon",
	"Asia/Saigon": "Asia/Ho_Chi_Minh",
	"Asia/Thimbu": "Asia/Thimphu",
	"Europe/Kiev": "Europe/Kyiv",
	"America/Godthab": "America/Nuuk",
	"Atlantic/Faeroe": "Atlantic/Faroe",
} as const

export function canonicalZone(zone: string): string {
	return RENAMED[zone as keyof typeof RENAMED] ?? zone
}

/** Every zone the browser knows, e.g. "Asia/Kolkata", with UTC in front. */
export function allTimeZones(): string[] {
	// UTC is absent from the runtime's list, hence the prepend.
	return ["UTC", ...Intl.supportedValuesOf("timeZone").map(canonicalZone)]
}

export function currentTimeZone(): string {
	return canonicalZone(Intl.DateTimeFormat().resolvedOptions().timeZone)
}

/**
 * Names a zone in one of Intl's styles.
 *
 * A zone the runtime does not recognise throws rather than returning nothing, and the
 * stored zone on an old event may well be one of those, so an unknown zone reads as
 * empty instead of taking the page down.
 */
function zoneName(zone: string, style: "longOffset" | "longGeneric", at: Date): string {
	try {
		return (
			new Intl.DateTimeFormat("en-GB", { timeZone: zone, timeZoneName: style })
				.formatToParts(at)
				.find((part) => part.type === "timeZoneName")?.value ?? ""
		)
	} catch {
		return ""
	}
}

/** The zone's offset on a given date, e.g. "GMT+05:30" — DST-aware. */
export function zoneOffsetLabel(zone: string, at: Date = new Date()): string {
	const offset = zoneName(zone, "longOffset", at)
	// Zero-offset zones format as a bare "GMT"; spell it out so every label reads alike.
	return offset === "GMT" ? "GMT+00:00" : offset
}

/** The place the zone is named for, e.g. "Asia/Kolkata" → "Kolkata". */
export function zoneCity(zone: string): string {
	return zone.split("/").pop()?.replace(/_/g, " ") ?? zone
}

/**
 * The zone's everyday name, e.g. "India Standard Time", "Eastern Time".
 *
 * The long form on purpose: it is the one that says "Eastern Time" rather than
 * "New York Time", and people search for the region name they think in.
 */
export function zoneGenericName(zone: string, at: Date = new Date()): string {
	return zoneName(zone, "longGeneric", at)
}

/**
 * Country of each zone, built once on first use.
 *
 * There is no zone-to-country lookup in Intl, but the reverse exists: asking a region
 * for its zones. Sweeping every two-letter code and inverting the result covers the
 * whole list — brute force, but nothing to keep up to date as tzdata moves. Costs
 * around 90ms, hence the memo.
 */
let zonesByCountry: Map<string, string> | null = null

function countryMap(): Map<string, string> {
	if (zonesByCountry) return zonesByCountry

	zonesByCountry = new Map()
	// Support for this is uneven; without it the picker simply shows no country.
	// TS has no type for this yet; the runtime check above is the real guard.
	type ZonedLocale = Intl.Locale & { getTimeZones?: () => string[] }
	if (typeof (Intl.Locale.prototype as ZonedLocale).getTimeZones !== "function")
		return zonesByCountry

	const names = new Intl.DisplayNames(["en"], { type: "region" })

	for (let first = 65; first <= 90; first++) {
		for (let second = 65; second <= 90; second++) {
			const code = String.fromCharCode(first, second)
			let zones: string[] = []
			try {
				zones = (new Intl.Locale(`und-${code}`) as ZonedLocale).getTimeZones?.() ?? []
			} catch {
				// Not a region code the runtime knows — most of the 676 are not.
			}
			if (!zones.length) continue

			const country = names.of(code) ?? code
			// The sweep returns legacy names, the same as `supportedValuesOf`.
			for (const zone of zones) zonesByCountry.set(canonicalZone(zone), country)
		}
	}

	return zonesByCountry
}

/** The country a zone sits in, e.g. "India". Empty when the runtime cannot say. */
export function zoneCountry(zone: string): string {
	return countryMap().get(zone) ?? ""
}

/**
 * Everything a zone should be findable by, as one string.
 *
 * Combobox matches on an option's label and value and nothing else, so the terms have
 * to be folded into the label. What the reader sees comes from the `#item` slot
 * instead, which is why this can afford to be a haystack rather than a caption.
 */
export function zoneSearchText(zone: string): string {
	return [zoneCity(zone), zoneCountry(zone), zoneGenericName(zone)]
		.filter(Boolean)
		.join(", ")
}
