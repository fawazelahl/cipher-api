from pathlib import Path


COVER_FIELDS = (
    "customer_name",
    "numeric_name",
    "manuscript_number",
)

BACKGROUND_FILE = Path(__file__).with_name("numeromancy_cover_background.png")

# Cover geometry — calibrated from the Emma Reynolds master cover.
NAME_Y = 1885
NUMERIC_NAME_Y = 2210
MANUSCRIPT_NUMBER_Y = 2480

# Customer names use adaptive sizing.
NAME_MAX_SIZE = 82
NAME_MIN_SIZE = 48
NAME_MAX_WIDTH = 1450

# Numeric fields use stable typography.
NUMERIC_NAME_SIZE = 140
MANUSCRIPT_NUMBER_SIZE = 105

GOLD = (205, 170, 95)
FONT_FILE = "DejaVuSerif.ttf"


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


def validate_background():
    if not BACKGROUND_FILE.exists():
        raise FileNotFoundError(
            f"COVER QC FAILED: background artwork not found: {BACKGROUND_FILE}"
        )

    return BACKGROUND_FILE


def validate_output_path(output_path):
    output_path = Path(output_path)

    if output_path.suffix.lower() not in {".png", ".pdf"}:
        raise ValueError(
            "COVER QC FAILED: output path must end in .png or .pdf"
        )

    return output_path


def fit_name_font(draw, text, font_loader):
    for size in range(NAME_MAX_SIZE, NAME_MIN_SIZE - 1, -1):
        font = font_loader(FONT_FILE, size)
        box = draw.textbbox((0, 0), text, font=font)
        rendered_width = box[2] - box[0]

        if rendered_width <= NAME_MAX_WIDTH:
            return font, size

    raise ValueError(
        "COVER QC FAILED: customer name cannot fit safely "
        f"within {NAME_MAX_WIDTH}px at minimum font size "
        f"{NAME_MIN_SIZE}px"
    )


def build_cover(customer_name, numeric_name, manuscript_number, output_path):
    data = validate_cover_data(
        customer_name,
        numeric_name,
        manuscript_number,
    )
    background_path = validate_background()
    output_path = validate_output_path(output_path)

    from PIL import Image, ImageDraw, ImageFont

    image = Image.open(background_path).convert("RGB")
    draw = ImageDraw.Draw(image)

    name_text = data["customer_name"].upper()
    numeric_text = str(data["numeric_name"])
    manuscript_text = str(data["manuscript_number"]).zfill(4)

    name_font, name_font_size = fit_name_font(
        draw,
        name_text,
        ImageFont.truetype,
    )
    numeric_font = ImageFont.truetype(
        FONT_FILE,
        NUMERIC_NAME_SIZE,
    )
    manuscript_font = ImageFont.truetype(
        FONT_FILE,
        MANUSCRIPT_NUMBER_SIZE,
    )

    center_x = image.width // 2

    draw.text(
        (center_x, NAME_Y),
        name_text,
        font=name_font,
        fill=GOLD,
        anchor="mm",
    )

    draw.text(
        (center_x, NUMERIC_NAME_Y),
        numeric_text,
        font=numeric_font,
        fill=GOLD,
        anchor="mm",
    )

    draw.text(
        (center_x, MANUSCRIPT_NUMBER_Y),
        manuscript_text,
        font=manuscript_font,
        fill=GOLD,
        anchor="mm",
    )

    image.save(output_path)

    return {
        "status": "cover_ready",
        "customer_name": name_text,
        "customer_name_font_size": name_font_size,
        "numeric_name": numeric_text,
        "manuscript_number": manuscript_text,
        "canvas_size": {
            "width": image.width,
            "height": image.height,
        },
        "output_path": str(output_path),
    }
