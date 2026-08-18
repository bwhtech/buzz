import type { ProposalSpeaker } from "@/types"

export interface Byline {
	/** The speaker the byline names first — "you" when that is the reader. */
	lead: string
	/** Everyone else, in listed order. A single name reads inline, more go behind a hover card. */
	rest: string[]
}

const displayName = (speaker: ProposalSpeaker): string =>
	[speaker.first_name, speaker.last_name].filter(Boolean).join(" ") || speaker.email

const isReader = (speaker: ProposalSpeaker, reader: string): boolean =>
	// User emails are stored lowercase; guest-entered speaker emails keep their casing.
	Boolean(reader) && speaker.email.toLowerCase() === reader.toLowerCase()

/** Reorders so the reader speaks first, and names them "you". */
function namesReaderFirst(speakers: ProposalSpeaker[], reader: string): string[] {
	const mine = speakers.filter((speaker) => isReader(speaker, reader))
	const theirs = speakers.filter((speaker) => !isReader(speaker, reader))

	return [...mine.map(() => "You"), ...theirs.map(displayName)]
}

export function speakerByline(speakers: ProposalSpeaker[], reader: string): Byline | null {
	const [lead, ...rest] = namesReaderFirst(speakers, reader)

	return lead ? { lead, rest } : null
}
