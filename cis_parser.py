import os
import json
import pdfplumber
import re
from tqdm import tqdm
from typing import Dict, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
# Define section patterns
DEFAULT_SECTIONS = {
    "profile": r"Profile Applicability:\s*(.*?)(?=\n\s*Description:|Rationale:|Impact:|Audit:|$)",
    "description": r"Description:\s*(.*?)(?=\n\s*Rationale:|Impact:|Audit:|$)",
    "rationale": r"Rationale:\s*(.*?)(?=\n\s*Impact:|Audit:|$)",
    "impact": r"Impact:\s*(.*?)(?=\n\s*Audit:|Remediation:|$)",
    "audit": r"Audit:\s*(.*?)(?=\n\s*Remediation:|$)",
    "remediation": r"Remediation:\s*(.*?)(?=\n\s*Default Value:|$)",
    "default_value": r"Default Value:\s*(.*?)(?=\n\s*References:|$)",
    "references": r"References:\s*(.*?)(?=\n\s*CIS Controls:|$)"
}
def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract full text from a PDF using pdfplumber."""
    logging.info(f"Reading PDF: {pdf_path}")
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in tqdm(pdf.pages, desc=f"Reading {os.path.basename(pdf_path)}"))


def parse_table_of_contents(text: str) -> Dict[str, List[Dict]]:
    """Extract the Table of Contents to map control IDs and titles."""
    match = re.search(r"Table of Contents\s*(.*?)(?=\n\s*Appendix)", text, re.DOTALL)
    if not match:
        logging.warning("Could not find Table of Contents.")
        return {}

    toc_text = match.group(1)
    pattern = re.compile(r"^\s*(?P<cisnum>\d+(\.\d+){1,3})\s+(?P<title>[\s\S]*?(?=\.))", re.MULTILINE)

    toc = {}
    for m in pattern.finditer(toc_text):
        control_id = m.group("cisnum").strip()
        category = control_id.split('.')[0]
        toc.setdefault(category, []).append({
            "id": control_id,
            "title": m.group("title").strip()
        })
    logging.info(f"Found {sum(len(v) for v in toc.values())} CIS entries.")
    return toc

def extract_cis_details(cis_id: str, full_text: str, next_id: Optional[str], sections: Dict[str, str]) -> Dict:
    """Extract detailed sections (audit, remediation, etc.) for a given control ID."""
    appendix_match = re.search(r"Appendix\s*(.*)", full_text, re.DOTALL)
    if not appendix_match:
        return {}

    appendix = appendix_match.group(1)
    pattern = (
        rf"({re.escape(cis_id)}.*?)(?=\n{re.escape(next_id)}|\Z)"
        if next_id else rf"({re.escape(cis_id)}.*?)(?=\Z)"
    )
    match = re.search(pattern, appendix, re.DOTALL)
    if not match:
        return {}

    details_text = match.group(1)
    parsed = {}
    for key, regex in sections.items():
        match = re.search(regex, details_text, re.DOTALL)
        if match:
            parsed[key] = match.group(1).strip()
    return parsed

def save_json(data: List[Dict], path: str):
    """Save structured data to a JSON file."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    logging.info(f"Saved output to {path}")

def parse_cis_benchmark(pdf_path: str, output_folder: str):
    """Parse a CIS Benchmark PDF and export its content to JSON."""
    logging.info(f"Starting CIS PDF parsing for {pdf_path}")
    full_text = extract_text_from_pdf(pdf_path)
    toc = parse_table_of_contents(full_text)
    if not toc:
        return

    expanded = []
    toc_keys = list(toc.keys())

    for section_index, (section, controls) in enumerate(toc.items()):
        for i, control in enumerate(controls):
            # Determine the next control ID for range-based extraction
            next_control = None
            if i + 1 < len(controls):
                next_control = controls[i + 1]['id']
            elif section_index + 1 < len(toc_keys):
                next_controls = toc[toc_keys[section_index + 1]]
                if next_controls:
                    next_control = next_controls[0]['id']

            details = extract_cis_details(control['id'], full_text, next_control, DEFAULT_SECTIONS)
            expanded.append({**control, **details})

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(output_folder, f"{base_name}.json")
    save_json(expanded, output_path)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parse a CIS Benchmark PDF to JSON")
    parser.add_argument("pdf_path", help="Path to the CIS Benchmark PDF file")
    parser.add_argument("output_folder", help="Folder to save the JSON output")

    args = parser.parse_args()

    parse_cis_benchmark(args.pdf_path, args.output_folder)
