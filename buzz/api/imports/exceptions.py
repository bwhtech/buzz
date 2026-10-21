from frappe import _lt

from buzz.api.exceptions import BuzzAPIError, Conflict, NotPermitted


class ImportRunning(Conflict):
	title = _lt("Import Running")
	message = _lt("An import is already running for this event. Wait for it to finish.")


class ImportsNotEnabled(NotPermitted):
	title = _lt("Imports Not Enabled")
	message = _lt("Imports are not enabled for this team. Contact your administrator.")


class UnreadableFile(BuzzAPIError):
	title = _lt("Unreadable File")
	message = _lt("This file could not be read. Upload a CSV or an Excel (.xlsx) file.")


class EmptySpreadsheet(BuzzAPIError):
	title = _lt("Nothing to Import")
	message = _lt("The file needs a header row and at least one row below it.")


class TooManyRows(BuzzAPIError):
	title = _lt("Too Many Rows")
	message = _lt("A file can hold up to {limit} rows. Split it and import each part.")


class ImportNotReady(BuzzAPIError):
	title = _lt("Not Ready")
	message = _lt("Sort out every issue before starting the import.")
