from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import tempfile
import time
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger("skyroute.pipeline")
INPUT_FIELDS = (
    "order_id",
    "shipment_id",
    "order_date",
    "dispatch_date",
    "delivery_date",
    "region",
    "carrier",
    "status",
    "shipping_cost",
    "weight_kg",
)
OUTPUT_FIELDS = (*INPUT_FIELDS, "dispatch_to_delivery_days")
VALID_STATUSES = {"Delivered", "In Transit", "Delayed"}


def _validate_row(row: dict[str, str | None]) -> dict[str, str]:
    for field in INPUT_FIELDS:
        if row.get(field) is None:
            raise ValueError(f"missing column value: {field}")

    clean = {field: (row[field] or "").strip() for field in INPUT_FIELDS}
    for field in ("order_id", "shipment_id", "order_date", "dispatch_date", "region", "carrier", "status"):
        if not clean[field]:
            raise ValueError(f"required value is blank: {field}")

    if clean["status"] not in VALID_STATUSES:
        raise ValueError("status is not recognised")

    try:
        order_date = date.fromisoformat(clean["order_date"])
        dispatch_date = date.fromisoformat(clean["dispatch_date"])
        delivery_date = date.fromisoformat(clean["delivery_date"]) if clean["delivery_date"] else None
    except ValueError as exc:
        raise ValueError("date must use YYYY-MM-DD") from exc

    if dispatch_date < order_date:
        raise ValueError("dispatch date precedes order date")
    if delivery_date and delivery_date < dispatch_date:
        raise ValueError("delivery date precedes dispatch date")
    if clean["status"] == "Delivered" and delivery_date is None:
        raise ValueError("delivered shipment has no delivery date")

    try:
        cost = Decimal(clean["shipping_cost"])
        weight = Decimal(clean["weight_kg"])
        cost_text = str(cost.quantize(Decimal("0.01")))
        weight_text = str(weight.quantize(Decimal("0.01")))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("shipping cost and weight must be numeric") from exc
    if not cost.is_finite() or cost < 0:
        raise ValueError("shipping cost must be a finite non-negative number")
    if not weight.is_finite() or weight < 0:
        raise ValueError("weight must be a finite non-negative number")

    clean["shipping_cost"] = cost_text
    clean["weight_kg"] = weight_text
    clean["dispatch_to_delivery_days"] = (
        str((delivery_date - dispatch_date).days) if delivery_date else ""
    )
    return clean


def _write_text_atomically(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            temporary_file.write(content)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def run_pipeline(
    input_path: str | Path,
    output_path: str | Path,
    summary_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate shipments, write the transformed CSV, and return a run summary."""
    started = time.monotonic()
    source = Path(input_path)
    destination = Path(output_path)
    summary_destination = Path(summary_path) if summary_path else destination.with_name(
        "pipeline_summary.json"
    )

    LOGGER.info("Pipeline started: input=%s", source.name)
    status_counts: Counter[str] = Counter()
    seen_shipments: set[str] = set()
    processed: list[dict[str, str]] = []
    rejections: list[dict[str, Any]] = []
    input_rows = 0

    try:
        with source.open("r", encoding="utf-8-sig", newline="") as input_file:
            reader = csv.DictReader(input_file)
            if reader.fieldnames is None:
                raise ValueError("input CSV is empty or has no header")
            missing_fields = sorted(set(INPUT_FIELDS) - set(reader.fieldnames))
            if missing_fields:
                raise ValueError(f"input CSV is missing required columns: {', '.join(missing_fields)}")

            for row_number, row in enumerate(reader, start=2):
                input_rows += 1
                try:
                    clean = _validate_row(row)
                    if clean["shipment_id"] in seen_shipments:
                        raise ValueError("duplicate shipment_id")
                    seen_shipments.add(clean["shipment_id"])
                    processed.append(clean)
                    status_counts[clean["status"]] += 1
                except ValueError as exc:
                    rejections.append({"row": row_number, "reason": str(exc)})
                    LOGGER.warning("Rejected input row %d: %s", row_number, exc)
    except OSError:
        LOGGER.exception("Could not read pipeline input: %s", source)
        raise

    csv_content = _csv_content(processed)
    total_cost = sum((Decimal(row["shipping_cost"]) for row in processed), Decimal("0"))
    total_weight = sum((Decimal(row["weight_kg"]) for row in processed), Decimal("0"))
    summary: dict[str, Any] = {
        "input_file": str(source),
        "output_file": str(destination),
        "input_rows": input_rows,
        "processed_rows": len(processed),
        "rejected_rows": len(rejections),
        "status_counts": dict(sorted(status_counts.items())),
        "total_shipping_cost": float(total_cost.quantize(Decimal("0.01"))),
        "average_weight_kg": (
            float((total_weight / len(processed)).quantize(Decimal("0.01")))
            if processed
            else 0.0
        ),
        "rejections": rejections,
    }

    _write_text_atomically(destination, csv_content)
    _write_text_atomically(
        summary_destination,
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
    )
    elapsed = time.monotonic() - started
    LOGGER.info(
        "Pipeline completed: input_rows=%d processed_rows=%d rejected_rows=%d duration_seconds=%.3f",
        input_rows,
        len(processed),
        len(rejections),
        elapsed,
    )
    return summary


def _csv_content(rows: list[dict[str, str]]) -> str:
    from io import StringIO

    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and summarise SkyRoute shipment data.")
    root = Path(__file__).resolve().parent
    parser.add_argument("--input", type=Path, default=root / "data" / "logistics_sample.csv")
    parser.add_argument(
        "--output", type=Path, default=root / "output" / "processed_shipments.csv"
    )
    parser.add_argument(
        "--summary", type=Path, default=root / "output" / "pipeline_summary.json"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    try:
        run_pipeline(args.input, args.output, args.summary)
    except (OSError, ValueError, csv.Error) as exc:
        LOGGER.error("Pipeline failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
