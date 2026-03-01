"""Post-build validation — probe the generated API for schema and endpoint coverage."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

from evals.config import CRUD_REQUEST_TIMEOUT, HEALTH_CHECK_TIMEOUT, HEALTH_RETRIES, HEALTH_RETRY_DELAY
from evals.scenarios import ExpectedEndpoint, ExpectedEntity, ExpectedField, Scenario

logger = logging.getLogger(__name__)


@dataclass
class EndpointResult:
    method: str
    path: str
    status_code: int | None = None
    success: bool = False
    error: str | None = None


@dataclass
class SchemaResult:
    entity_name: str
    fields_expected: int = 0
    fields_found: int = 0
    missing_fields: list[str] = field(default_factory=list)
    extra_fields: list[str] = field(default_factory=list)
    score: float = 0.0  # 0.0 to 1.0


@dataclass
class ValidationResult:
    """Output of post-build validation."""
    api_url: str
    healthy: bool = False
    openapi_fetched: bool = False
    openapi_paths: list[str] = field(default_factory=list)

    endpoint_results: list[EndpointResult] = field(default_factory=list)
    schema_results: list[SchemaResult] = field(default_factory=list)

    endpoint_coverage: float = 0.0     # fraction of expected endpoints that return 2xx
    schema_match_score: float = 0.0    # average schema match across entities

    errors: list[str] = field(default_factory=list)


def _normalize(name: str) -> str:
    """Normalize entity/field name for fuzzy matching."""
    return name.lower().replace("_", "").replace("-", "")


def _pluralize(name: str) -> str:
    """Naive pluralization for endpoint path matching."""
    n = name.lower()
    if n.endswith("y"):
        return n[:-1] + "ies"
    if n.endswith("s"):
        return n + "es"
    return n + "s"


def _type_matches(expected_type: str, actual_type: str) -> bool:
    """Check if an OpenAPI type loosely matches our expected type hint."""
    actual = actual_type.lower()
    mapping = {
        "str": {"string"},
        "text": {"string"},
        "int": {"integer", "int"},
        "float": {"number", "float", "double"},
        "bool": {"boolean", "bool"},
        "datetime": {"string"},  # datetime is often string format in OpenAPI
    }
    expected_types = mapping.get(expected_type, {expected_type})
    return actual in expected_types


async def _check_health(api_url: str) -> bool:
    """Wait for the generated API to be healthy."""
    import asyncio
    for attempt in range(HEALTH_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT) as client:
                resp = await client.get(f"{api_url}/health")
                if resp.status_code == 200:
                    return True
        except Exception:
            pass

        # Try /docs as fallback
        try:
            async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT) as client:
                resp = await client.get(f"{api_url}/docs")
                if resp.status_code == 200:
                    return True
        except Exception:
            pass

        if attempt < HEALTH_RETRIES - 1:
            await asyncio.sleep(HEALTH_RETRY_DELAY)

    return False


async def _fetch_openapi(api_url: str) -> dict | None:
    """Fetch the OpenAPI spec from the generated API."""
    try:
        async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT) as client:
            resp = await client.get(f"{api_url}/openapi.json")
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning("Failed to fetch OpenAPI spec: %s", e)
    return None


def _validate_schema_from_openapi(
    openapi: dict,
    entity: ExpectedEntity,
) -> SchemaResult:
    """Check if an entity's fields appear in the OpenAPI schemas."""
    result = SchemaResult(
        entity_name=entity.name,
        fields_expected=len(entity.fields),
    )

    schemas = openapi.get("components", {}).get("schemas", {})
    if not schemas:
        result.missing_fields = [f.name for f in entity.fields]
        return result

    # Find the matching schema (try various naming conventions)
    entity_norm = _normalize(entity.name)
    matched_schema = None
    for schema_name, schema_def in schemas.items():
        norm = _normalize(schema_name)
        # Match: "Todo", "TodoCreate", "TodoBase", "TodoSchema"
        if norm.startswith(entity_norm) or entity_norm.startswith(norm):
            # Prefer the one with most properties (likely the "read" or "base" schema)
            props = schema_def.get("properties", {})
            if matched_schema is None or len(props) > len(matched_schema.get("properties", {})):
                matched_schema = schema_def

    if not matched_schema:
        result.missing_fields = [f.name for f in entity.fields]
        return result

    schema_props = matched_schema.get("properties", {})
    schema_prop_norms = {_normalize(k): (k, v) for k, v in schema_props.items()}

    found = 0
    for ef in entity.fields:
        ef_norm = _normalize(ef.name)
        if ef_norm in schema_prop_norms:
            found += 1
        else:
            result.missing_fields.append(ef.name)

    # Extra fields (excluding id, created_at, updated_at which are auto-generated)
    expected_norms = {_normalize(f.name) for f in entity.fields}
    auto_fields = {"id", "createdat", "updatedat", "createdon", "updatedon"}
    for norm_name, (orig_name, _) in schema_prop_norms.items():
        if norm_name not in expected_norms and norm_name not in auto_fields:
            # Foreign keys are OK — don't count as extra
            if not orig_name.endswith("_id"):
                result.extra_fields.append(orig_name)

    result.fields_found = found
    if result.fields_expected > 0:
        result.score = found / result.fields_expected
    else:
        result.score = 1.0

    return result


async def _probe_endpoint(
    client: httpx.AsyncClient,
    api_url: str,
    endpoint: ExpectedEndpoint,
) -> EndpointResult:
    """Try hitting a single endpoint and check if it responds with 2xx."""
    # Replace {id} with 1 for path params
    path = endpoint.path.replace("{id}", "1")
    url = f"{api_url}{path}"

    result = EndpointResult(method=endpoint.method, path=endpoint.path)

    try:
        if endpoint.method == "GET":
            resp = await client.get(url)
        elif endpoint.method == "POST":
            # Send minimal valid JSON body
            resp = await client.post(url, json={})
        elif endpoint.method == "PUT":
            resp = await client.put(url, json={})
        elif endpoint.method == "DELETE":
            resp = await client.delete(url)
        else:
            result.error = f"Unknown method: {endpoint.method}"
            return result

        result.status_code = resp.status_code
        # For GET list endpoints, 200 is success
        # For GET by id, 404 is acceptable (no data yet)
        # For POST with empty body, 422 is acceptable (validation error = endpoint exists)
        # For DELETE, 404 is acceptable
        if endpoint.method == "GET" and "{id}" not in endpoint.path:
            result.success = resp.status_code == 200
        elif endpoint.method == "POST":
            result.success = resp.status_code in (200, 201, 422)
        elif endpoint.method in ("PUT", "DELETE"):
            result.success = resp.status_code in (200, 204, 404, 422)
        elif endpoint.method == "GET":
            result.success = resp.status_code in (200, 404)

    except Exception as e:
        result.error = str(e)

    return result


async def validate(
    scenario: Scenario,
    api_url: str,
) -> ValidationResult:
    """Run full post-build validation against a generated API.

    1. Health check
    2. Fetch OpenAPI spec → schema validation
    3. Probe expected endpoints → coverage score
    """
    vr = ValidationResult(api_url=api_url)

    # ── 1. Health check ────────────────────────────────────────
    vr.healthy = await _check_health(api_url)
    if not vr.healthy:
        vr.errors.append(f"API not healthy at {api_url}")
        logger.warning("[%s] API not healthy, skipping further validation", scenario.id)
        return vr

    # ── 2. OpenAPI spec + schema validation ────────────────────
    openapi = await _fetch_openapi(api_url)
    if openapi:
        vr.openapi_fetched = True
        paths = openapi.get("paths", {})
        vr.openapi_paths = list(paths.keys())

        for entity in scenario.entities:
            sr = _validate_schema_from_openapi(openapi, entity)
            vr.schema_results.append(sr)
            logger.info(
                "[%s] Schema %s: %d/%d fields found (score: %.2f)",
                scenario.id, entity.name, sr.fields_found, sr.fields_expected, sr.score,
            )
    else:
        vr.errors.append("Could not fetch OpenAPI spec")
        # Still try endpoint probing
        for entity in scenario.entities:
            vr.schema_results.append(SchemaResult(
                entity_name=entity.name,
                fields_expected=len(entity.fields),
                missing_fields=[f.name for f in entity.fields],
            ))

    # ── 3. Endpoint probing ────────────────────────────────────
    async with httpx.AsyncClient(timeout=CRUD_REQUEST_TIMEOUT) as client:
        for ep in scenario.endpoints:
            er = await _probe_endpoint(client, api_url, ep)
            vr.endpoint_results.append(er)
            if er.success:
                logger.debug("[%s] %s %s → %s ✓", scenario.id, ep.method, ep.path, er.status_code)
            else:
                logger.info(
                    "[%s] %s %s → %s %s",
                    scenario.id, ep.method, ep.path,
                    er.status_code or "ERR", er.error or "",
                )

    # ── Compute aggregate scores ───────────────────────────────
    if vr.endpoint_results:
        successes = sum(1 for er in vr.endpoint_results if er.success)
        vr.endpoint_coverage = successes / len(vr.endpoint_results)

    if vr.schema_results:
        vr.schema_match_score = sum(sr.score for sr in vr.schema_results) / len(vr.schema_results)

    return vr
