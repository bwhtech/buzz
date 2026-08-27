import confetti, { type Options as ConfettiOptions } from "canvas-confetti"

/**
 * Utility function to create a random number within a range
 * @param {number} min - Minimum value
 * @param {number} max - Maximum value
 * @returns {number} Random number between min and max
 */
const randomInRange = (min: number, max: number): number => Math.random() * (max - min) + min

/**
 * Triggers a celebratory confetti animation
 * @param {Object} options - Configuration options for the confetti
 * @param {number} options.particleCount - Base particle count (default: 50)
 * @param {number} options.startVelocity - Starting velocity of particles (default: 30)
 * @param {number} options.spread - Spread angle of particles (default: 360)
 */
export const triggerCelebrationConfetti = (options: ConfettiOptions = {}): void => {
	const { particleCount = 50, startVelocity = 30, spread = 360 } = options
	const duration = 3000

	const animationEnd = Date.now() + duration

	const interval = setInterval(() => {
		const timeLeft = animationEnd - Date.now()

		if (timeLeft <= 0) {
			clearInterval(interval)
			return
		}

		const currentParticleCount = particleCount * (timeLeft / duration)

		// Left side confetti burst
		confetti({
			particleCount: currentParticleCount,
			startVelocity,
			spread,
			origin: {
				x: randomInRange(0.1, 0.3),
				y: Math.random() - 0.2,
			},
		})

		// Right side confetti burst
		confetti({
			particleCount: currentParticleCount,
			startVelocity,
			spread,
			origin: {
				x: randomInRange(0.7, 0.9),
				y: Math.random() - 0.2,
			},
		})
	}, 250)
}

/**
 * Triggers a simple single-burst confetti animation
 * @param {Object} options - Configuration options
 */
export const triggerSimpleConfetti = (options: ConfettiOptions = {}): void => {
	const {
		particleCount = 100,
		startVelocity = 30,
		spread = 360,
		origin = { x: 0.5, y: 0.5 },
	} = options

	confetti({
		particleCount,
		startVelocity,
		spread,
		origin,
	})
}
