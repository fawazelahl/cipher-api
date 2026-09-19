from pathlib import Path
import shutil
import subprocess

from pypdf import PdfReader


EXPECTED_MANUSCRIPT_PAGES = 29


def convert_docx_to_pdf(docx_path, output_path):
    docx_path = Path(docx_path).resolve()
    output_path = Path(output_path).resolve()

    if not docx_path.is_file():
        raise FileNotFoundError(f"DOCX file not found: {docx_path}")

    libreoffice = shutil.which("libreoffice") or shutil.which("soffice")

    if not libreoffice:
        raise RuntimeError(
            "LibreOffice is required for DOCX-to-PDF conversion."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            libreoffice,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_path.parent),
            str(docx_path),
        ],
        check=True,
    )

    generated_pdf = output_path.parent / f"{docx_path.stem}.pdf"

    if not generated_pdf.is_file():
        raise FileNotFoundError(
            f"LibreOffice did not create the expected PDF: {generated_pdf}"
        )

    if generated_pdf != output_path:
        if output_path.exists():
            output_path.unlink()
        generated_pdf.replace(output_path)

    reader = PdfReader(str(output_path))
    page_count = len(reader.pages)

    if page_count != EXPECTED_MANUSCRIPT_PAGES:
        raise ValueError(
            f"DOCX-to-PDF QC failed: expected "
            f"{EXPECTED_MANUSCRIPT_PAGES} pages, got {page_count}."
        )

    return {
        "status": "docx_to_pdf_passed",
        "input_path": str(docx_path),
        "output_path": str(output_path),
        "page_count": page_count,
    }
