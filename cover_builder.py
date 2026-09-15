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

BACKGROUND_FILE = Path(__file__).with_name("numeromancy_cover_background.png")

def validate_background():
    if not BACKGROUND_FILE.exists():
        raise FileNotFoundError(
            f"COVER QC FAILED: background artwork not found: {BACKGROUND_FILE}"
        )
    return BACKGROUND_FILE

def build_cover(customer_name, numeric_name, manuscript_number, output_path):
        data = validate_cover_data(customer_name, numeric_name, manuscript_number)
        background_path = validate_background()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return {
            "status": "cover_ready",
            "customer_name": data["customer_name"],
            "numeric_name": data["numeric_name"],
                    "manuscript_number": data["manuscript_number"],
                    "background_file": str(background_path),
                    "output_path": str(output_path),
                }

def validate_output_path(output_path):
    output_path = Path(output_path)
    if output_path.suffix.lower() not in {".png", ".pdf"}:
        raise ValueError(
            "COVER QC FAILED: output path must end in .png or .pdf"
            )
        return output_path
def build_cover(customer_name, numeric_name, manuscript_number, output_path):
        data = validate_cover_data(customer_name, numeric_name, manuscript_number)
    background_path = validate_background()
output_path = validate_output_path(output_path)
from PIL import Image, ImageDraw, ImageFont
image = Image.open(background_path).convert("RGB")
draw = ImageDraw.Draw(image)
gold = (205, 170, 95)
name_font = ImageFont.truetype("DejaVuSerif.ttf", 64)
number_font = ImageFont.truetype("DejaVuSerif.ttf", 58)
name_text = data["customer_name"].upper()
numeric_text = str(data["numeric_name"])
manuscript_text = str(data["manuscript_number"]).zfill(4)
draw.text((image.width // 2, 1260), name_text, font=name_font, fill=gold, anchor="mm")
draw.text((image.width // 2, 1740), numeric_text, font=number_font, fill=gold, anchor="mm")
draw.text((image.width // 2, 2045), manuscript_text, font=number_font, fill=gold, anchor="mm")
image.save(output_path)
return {
    "status": "cover_ready",
    "customer_name": name_text,
    "numeric_name": numeric_text,
    "manuscript_number": manuscript_text,
    "output_path": str(output_path),
    }
