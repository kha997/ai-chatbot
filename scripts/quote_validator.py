"""Validate a synthetic draft quote against a trusted tenant catalog."""

import re
from collections.abc import Mapping
from datetime import datetime
from decimal import Context, Decimal, localcontext


TENANTS = {"NHD", "HANU", "ZENA"}
SKU = re.compile(r"SYN-[A-Z0-9]+(?:-[A-Z0-9]+)*")
TOKEN = re.compile(r"[a-z][a-z0-9-]*")
SOURCE_ID = re.compile(r"([A-Z]+)-pricing-v[1-9][0-9]*")
WHOLE_COUNT = re.compile(r"[0-9]+")
AMOUNT = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
UTC_TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")


def _matches(pattern, value):
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _utc(value):
    if _matches(UTC_TIMESTAMP, value):
        try:
            return datetime.fromisoformat(value[:-1] + "+00:00")
        except ValueError:
            return None
    return None


def validate_quote(*, context, request, candidate, sources, as_of):
    """Return the accepted fixture oracle shape without mutating inputs.

    The caller supplies authenticated tenant context, the canonical catalog and
    an authoritative UTC clock. Request and candidate are untrusted data.
    """
    tenant = context.get("tenant") if isinstance(context, Mapping) else None
    if not isinstance(tenant, str) or tenant not in TENANTS:
        return {"behavior": "refuse", "reason": "requested_tenant_mismatch"}
    if not isinstance(request, Mapping):
        return {"behavior": "clarify", "reason": "unknown_sku"}
    if "tenant" in request or request.get("requested_tenant", tenant) != tenant:
        return {"behavior": "refuse", "reason": "requested_tenant_mismatch"}

    sku = request.get("sku")
    if not _matches(SKU, sku):
        return {"behavior": "clarify", "reason": "unknown_sku"}
    active_sources = context.get("active_sources")
    if not isinstance(active_sources, (list, tuple)):
        return {"behavior": "refuse", "reason": "source_revision_mismatch"}
    bindings = [
        binding for binding in active_sources
        if isinstance(binding, Mapping) and binding.get("tenant") == tenant and binding.get("sku") == sku
    ]
    if not bindings:
        return {"behavior": "clarify", "reason": "unknown_sku"}
    if len(bindings) != 1:
        return {"behavior": "refuse", "reason": "source_revision_mismatch"}
    binding = bindings[0]

    quantity = request.get("quantity")
    if not _matches(WHOLE_COUNT, quantity) or Decimal(quantity).is_zero():
        return {"behavior": "clarify", "reason": "invalid_quantity"}
    if not isinstance(candidate, Mapping):
        return {"behavior": "refuse", "reason": "source_unknown"}
    source_id = candidate.get("source_id")
    if not _matches(SOURCE_ID, source_id):
        return {"behavior": "refuse", "reason": "source_unknown"}
    # Classify a foreign identifier using only the supplied string. Do not
    # query any foreign catalog to determine whether that identifier exists.
    if source_id.partition("-")[0] != tenant:
        return {"behavior": "refuse", "reason": "source_tenant_mismatch"}
    if not isinstance(sources, (list, tuple)):
        return {"behavior": "refuse", "reason": "source_unknown"}
    records = [
        source for source in sources
        if isinstance(source, Mapping) and source.get("tenant") == tenant and source.get("source_id") == source_id
    ]
    if not records:
        return {"behavior": "refuse", "reason": "source_unknown"}
    if len(records) != 1:
        return {"behavior": "refuse", "reason": "source_revision_mismatch"}
    source = records[0]

    version = source.get("version")
    versions = (version, binding.get("version"), candidate.get("version"))
    if (source.get("sku") != sku or binding.get("source_id") != source_id
            or any(type(value) is not int or value <= 0 for value in versions)
            or versions[1:] != (version, version)
            or source_id != f"{tenant}-pricing-v{version}"):
        return {"behavior": "refuse", "reason": "source_revision_mismatch"}
    status = source.get("status")
    if status != "approved":
        reason = "source_revoked" if status == "revoked" else "source_unapproved"
        return {"behavior": "refuse", "reason": reason}
    start, now, end = map(_utc, (source.get("valid_from"), as_of, source.get("valid_until")))
    if None in (start, now, end) or not start <= now < end:
        return {"behavior": "refuse", "reason": "source_expired"}

    unit = source.get("unit")
    if not _matches(TOKEN, unit) or request.get("unit") != unit:
        return {"behavior": "clarify", "reason": "unit_mismatch"}
    if source.get("currency") != "VND" or request.get("currency") != "VND":
        return {"behavior": "clarify", "reason": "currency_mismatch"}
    paragraph = source.get("paragraph_id")
    citation = source.get("citation")
    if not _matches(TOKEN, paragraph) or citation != f"{source_id}#{paragraph}" or candidate.get("citation") != citation:
        return {"behavior": "refuse", "reason": "citation_mismatch"}
    unit_price, minimum = source.get("unit_price"), source.get("minimum")
    if not _matches(AMOUNT, unit_price) or not _matches(AMOUNT, minimum):
        return {"behavior": "refuse", "reason": "source_price_missing"}

    # Operand lengths cover the exact coefficient of a finite decimal product.
    precision = max(len(quantity) + len(unit_price), len(minimum))
    with localcontext(Context(prec=precision)):
        total = max(Decimal(quantity) * Decimal(unit_price), Decimal(minimum))
    return {"behavior": "answer", "reason": "quoted", "total": format(total, "f"), "currency": "VND",
            "citation": citation}
