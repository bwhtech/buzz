from pydantic import BaseModel, ConfigDict


class APIRequest(BaseModel):
	model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class APIResponse(BaseModel):
	model_config = ConfigDict(extra="forbid")

	def __json__(self) -> dict:
		# frappe's json_handler checks __json__ before its Iterable branch; without this a
		# BaseModel serializes as a list of (key, value) pairs.
		return self.model_dump()
