from pydantic import BaseModel, ConfigDict


class APIRequest(BaseModel):
	model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class APIResponse(BaseModel):
	model_config = ConfigDict(extra="forbid")

	def __json__(self) -> dict:
		# frappe's json_handler checks __json__ before its Iterable branch; without this a
		# BaseModel serializes as a list of (key, value) pairs.
		# Not model_dump(): frappe._dict answers every attribute lookup via dict.get, so
		# pydantic mistakes untyped rows for models carrying a None serializer and dies.
		return {name: jsonify_value(getattr(self, name)) for name in type(self).model_fields}


def jsonify_value(value):
	if isinstance(value, APIResponse):
		return value.__json__()
	if isinstance(value, list):
		return [jsonify_value(item) for item in value]
	return value
