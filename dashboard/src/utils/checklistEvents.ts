export type DoneStep = {
	step: string
	group: string
}

type ChecklistEvent = [name: string, properties?: DoneStep]

// `sent` is null on the first load, which sets the baseline and sends nothing.
export function checklistEvents(
	sent: string[] | null,
	done: DoneStep[],
	essentials: string[],
): ChecklistEvent[] {
	if (!sent) return []
	const events: ChecklistEvent[] = done
		.filter((step) => !sent.includes(step.step))
		.map((step) => ["checklist_step_completed", step])
	const names = done.map((step) => step.step)
	const allDone = (list: string[]) => essentials.every((name) => list.includes(name))
	if (!allDone(sent) && allDone(names)) events.push(["checklist_completed"])
	return events
}
