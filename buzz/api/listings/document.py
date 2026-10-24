from frappe.utils import get_url

from buzz.api.listings.schemas import EventListing

METHOD_PATH = "/api/v2/method/buzz.api.listings"
SCHEMA_REF = {"$ref": "#/components/schemas/EventListing"}


def operation(summary: str, body_properties: dict, required: str) -> dict:
	body = {"type": "object", "properties": body_properties, "required": [required]}
	return {
		"post": {
			"summary": summary,
			"security": [{"tokenAuth": []}],
			"requestBody": {"required": True, "content": {"application/json": {"schema": body}}},
			"responses": {"200": {"description": "Done"}},
		}
	}


def openapi_document() -> dict:
	return {
		"openapi": "3.1.0",
		"info": {"title": "Buzz partner event listings", "version": "1.0.0"},
		"servers": [{"url": get_url()}],
		"paths": {
			f"{METHOD_PATH}.upsert_event": operation(
				"List an event, or update it when the source_id is known", {"event": SCHEMA_REF}, "event"
			),
			f"{METHOD_PATH}.remove_event": operation(
				"Take an event off the community page",
				{"source_id": {"type": "string", "maxLength": 140}},
				"source_id",
			),
		},
		"components": {
			"schemas": {"EventListing": EventListing.model_json_schema()},
			"securitySchemes": {
				"tokenAuth": {
					"type": "apiKey",
					"in": "header",
					"name": "Authorization",
					"description": "token <api_key>:<api_secret>",
				}
			},
		},
	}
