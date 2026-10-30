from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, NotPermitted, ResourceNotFound


class PlaygroundDisabled(ResourceNotFound):
	message = _lt("The playground is not enabled on this site.")


class NotInSandbox(NotPermitted):
	message = _lt("Start a playground sandbox first.")


class UnknownPersona(BuzzAPIError):
	title = _lt("Invalid Persona")
	message = _lt("{persona} is not a playground persona.")
