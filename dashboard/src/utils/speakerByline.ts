export interface BylineSpeaker {
	first_name: string
	last_name: string | null
	email: string
}

export interface Byline {
	/** The speaker the byline names first — "you" when that is the reader. */
	lead: string
	/** The other half of a pair. Null unless there are exactly two speakers. */
	partner: string | null
	/** Everyone the byline leaves for the hover card. Empty below three speakers. */
	others: string[]
}

const displayName = (speaker: BylineSpeaker): string =>
	[speaker.first_name, speaker.last_name].filter(Boolean).join(" ") || speaker.email

const isReader = (speaker: BylineSpeaker, reader: string): boolean =>
	// User emails are stored lowercase; guest-entered speaker emails keep their casing.
	Boolean(reader) && speaker.email.toLowerCase() === reader.toLowerCase()

/** Reorders so the reader speaks first, and names them "you". */
function namesReaderFirst(speakers: BylineSpeaker[], reader: string): string[] {
	const mine = speakers.filter((speaker) => isReader(speaker, reader))
	const theirs = speakers.filter((speaker) => !isReader(speaker, reader))

	return [...mine.map(() => "You"), ...theirs.map(displayName)]
}

export function speakerByline(speakers: BylineSpeaker[], reader: string): Byline | null {
	const [lead, ...rest] = namesReaderFirst(speakers, reader)
	if (!lead) return null

	return {
		lead,
		partner: rest.length === 1 ? rest[0] : null,
		others: rest.length > 1 ? rest : [],
	}
}
