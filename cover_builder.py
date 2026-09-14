from pathlib import Path


COVER_FIELDS = (
    "customer_name",
    "numeric_name",
    "manuscript_number",
)


def validate_cover_data(customer_name, numeric_name, manuscript_number):
    values = {
        "customer_name": customer_name,
        "numeric_name": numeric_name,
        "manuscript_number": manuscript_number,
    }

    missing = [
        field
        for field in COVER_FIELDS
        if values.get(field) is None or str(values.get(field)).strip() == ""
    ]

    if missing:
        raise ValueError(
            "COVER QC FAILED: missing required field(s): "
            + ", ".join(missing)
        )

    return {
        "status": "cover_data_passed",
        "customer_name": str(customer_name).strip(),
        "numeric_name": str(numeric_name).strip(),
        "manuscript_number": str(manuscript_number).strip(),
    }
