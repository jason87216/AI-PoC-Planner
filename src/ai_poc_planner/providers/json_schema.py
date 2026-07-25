"""Conservative JSON Schema normalization for constrained providers."""

from __future__ import annotations

from copy import deepcopy


class ProviderSchemaUnsupportedError(ValueError):
    """A safe local error: no provider request was made."""


def normalize_provider_schema(schema: dict[str, object]) -> dict[str, object]:
    """Inline local refs and remove annotations unsupported by llama.cpp grammar.

    This intentionally rejects unions rather than silently weakening the final
    Pydantic contract.  Phase-specific provider contracts must avoid unions.
    """

    definitions = schema.get("$defs", {})
    if not isinstance(definitions, dict):
        raise ProviderSchemaUnsupportedError("invalid schema definitions")

    def visit(value: object) -> object:
        if isinstance(value, list):
            return [visit(item) for item in value]
        if not isinstance(value, dict):
            return value
        if "$ref" in value:
            reference = value["$ref"]
            if not isinstance(reference, str) or not reference.startswith("#/$defs/"):
                raise ProviderSchemaUnsupportedError("unsupported schema reference")
            target = definitions.get(reference.rsplit("/", 1)[1])
            if not isinstance(target, dict):
                raise ProviderSchemaUnsupportedError("missing schema reference")
            return visit(deepcopy(target))
        if any(key in value for key in ("anyOf", "oneOf", "allOf", "not")):
            raise ProviderSchemaUnsupportedError("provider schema contains a union")
        result: dict[str, object] = {}
        for key, item in value.items():
            if key in {
                "$defs",
                "title",
                "description",
                "default",
                "format",
                "discriminator",
            }:
                continue
            result[key] = visit(item)
        if result.get("type") == "object":
            result["additionalProperties"] = False
            properties = result.get("properties")
            if isinstance(properties, dict):
                result["required"] = sorted(properties)
        return result

    normalized = visit(schema)
    if not isinstance(normalized, dict):
        raise ProviderSchemaUnsupportedError("schema root is invalid")
    return normalized
