"""Arithmetic checks. A check that can't be done says so; it never passes by default."""

from decimal import Decimal

PASSED, FAILED, NOT_CHECKABLE = "Passed", "Failed", "Not checkable"
TOLERANCE = Decimal("0.01")


def _close(a, b):
    return abs(a - b) <= TOLERANCE


def check_line(quantity, unit_price, line_discount, line_total):
    """Quantity × unit price, less any discount amount, against the line total."""
    if quantity is None or unit_price is None or line_total is None:
        return NOT_CHECKABLE
    expected = quantity * unit_price - abs(line_discount or 0)
    return PASSED if _close(expected, line_total) else FAILED


def check_document(amounts, line_totals):
    """Check the document's summary figures.

    amounts: dict with Decimal or None for subtotal, discount, shipping, tax_amount, total,
    balance_due. When no total is printed, the balance due is checked in its place: it can
    include earlier balances or payments, so a mismatch is flagged but never corrected.
    line_totals: list of Decimal or None, one per line item.
    Returns (overall status, list of failed check ids).
    """
    failures = []
    subtotal, total = amounts.get("subtotal"), amounts.get("total")
    total_failure = "total_mismatch"
    if total is None and amounts.get("balance_due") is not None:
        total, total_failure = amounts["balance_due"], "balance_mismatch"
    lines_known = bool(line_totals) and all(t is not None for t in line_totals)
    lines_sum = sum(line_totals) if lines_known else None

    if subtotal is not None and lines_sum is not None and not _close(lines_sum, subtotal):
        failures.append("subtotal_mismatch")

    base = subtotal if subtotal is not None else lines_sum
    total_checked = False
    if base is not None and total is not None:
        total_checked = True
        tax = amounts.get("tax_amount") or 0
        shipping = amounts.get("shipping") or 0
        discount = abs(amounts.get("discount") or 0)
        candidates = {base + tax + shipping - discount}
        if discount:
            # Some layouts show the discount but have already taken it off the subtotal.
            candidates.add(base + tax + shipping)
        if not any(_close(c, total) for c in candidates):
            failures.append(total_failure)

    if failures:
        return FAILED, failures
    return (PASSED if total_checked else NOT_CHECKABLE), failures
