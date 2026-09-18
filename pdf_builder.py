from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image
from pypdf import PdfReader, PdfWriter, PageObject, Transformation


EXPECTED_MANUSCRIPT_PAGES = 29
EXPECTED_FINAL_PAGES = 30


def validate_input_file(path, label, allowed_suffixes):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"PDF ASSEMBLY QC FAILED: {label} not found: {path}"
        )

    if path.suffix.lower() not in allowed_suffixes:
        raise ValueError(
            f"PDF ASSEMBLY QC FAILED: {label} must be one of "
            f"{sorted(allowed_suffixes)}"
        )

    return path


def validate_output_path(output_path):
    output_path = Path(output_path)

    if output_path.suffix.lower() != ".pdf":
        raise ValueError(
            "PDF ASSEMBLY QC FAILED: output path must end in .pdf"
        )

    return output_path


def build_cover_page(cover_image_path, target_width, target_height):
    with Image.open(cover_image_path) as source:
        image = source.convert("RGB")

        with NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            image.save(temp_path, "PDF", resolution=72.0)

            cover_reader = PdfReader(str(temp_path))
            source_page = cover_reader.pages[0]

            source_width = float(source_page.mediabox.width)
            source_height = float(source_page.mediabox.height)

            scale = min(
                target_width / source_width,
                target_height / source_height,
            )

            scaled_width = source_width * scale
            scaled_height = source_height * scale

            translate_x = (target_width - scaled_width) / 2
            translate_y = (target_height - scaled_height) / 2

            cover_page = PageObject.create_blank_page(
                width=target_width,
                height=target_height,
            )

            source_page.add_transformation(
                Transformation()
                .scale(scale)
                .translate(translate_x, translate_y)
            )

            cover_page.merge_page(source_page)

            return cover_page

        finally:
            temp_path.unlink(missing_ok=True)


def assemble_final_pdf(
    cover_image_path,
    manuscript_pdf_path,
    output_path,
):
    cover_image_path = validate_input_file(
        cover_image_path,
        "cover image",
        {".png", ".jpg", ".jpeg"},
    )

    manuscript_pdf_path = validate_input_file(
        manuscript_pdf_path,
        "manuscript PDF",
        {".pdf"},
    )

    output_path = validate_output_path(output_path)

    manuscript_reader = PdfReader(str(manuscript_pdf_path))
    manuscript_page_count = len(manuscript_reader.pages)

    if manuscript_page_count != EXPECTED_MANUSCRIPT_PAGES:
        raise ValueError(
            "PDF ASSEMBLY QC FAILED: canonical manuscript must contain "
            f"exactly {EXPECTED_MANUSCRIPT_PAGES} pages; "
            f"found {manuscript_page_count}"
        )

    first_page = manuscript_reader.pages[0]
    target_width = float(first_page.mediabox.width)
    target_height = float(first_page.mediabox.height)

    cover_page = build_cover_page(
        cover_image_path,
        target_width,
        target_height,
    )

    writer = PdfWriter()
    writer.add_page(cover_page)

    for page in manuscript_reader.pages:
        writer.add_page(page)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("wb") as output_file:
        writer.write(output_file)

    final_reader = PdfReader(str(output_path))
    final_page_count = len(final_reader.pages)

    if final_page_count != EXPECTED_FINAL_PAGES:
        output_path.unlink(missing_ok=True)

        raise ValueError(
            "PDF ASSEMBLY QC FAILED: assembled PDF must contain "
            f"exactly {EXPECTED_FINAL_PAGES} pages; "
            f"found {final_page_count}"
        )

    return {
        "status": "pdf_assembly_passed",
        "cover_pages": 1,
        "manuscript_pages": manuscript_page_count,
        "final_pages": final_page_count,
        "output_path": str(output_path),
    }
