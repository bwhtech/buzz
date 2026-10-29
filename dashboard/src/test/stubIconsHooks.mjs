export function resolve(specifier, context, nextResolve) {
	if (!specifier.startsWith("~icons/")) return nextResolve(specifier, context)
	return { url: "data:text/javascript,export default {}", shortCircuit: true }
}
