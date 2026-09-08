"""
Extraction pipeline for "guide_2026_tp.pdf" (Tunisian university admission-capacity guide).

Produces one structured record per (institution x orientation code), each holding
the list of admission options (one per baccalaureate stream).
"""
import pdfplumber
import re
import unicodedata
import json
import sys
from collections import OrderedDict

PDF_PATH = sys.argv[1] if len(sys.argv) > 1 else "guide_2026_tp.pdf"
OUTPUT_PATH = sys.argv[2] if len(sys.argv) > 2 else "guide_2026_structured.json"

# ---------------------------------------------------------------------------
# 1. Arabic bidi fix-up
#    pdfplumber pulls glyphs in the order they're painted in the PDF content
#    stream. For this document's RTL Arabic runs that order is visually
#    reversed; embedded numbers/Latin formulas are already correct and must
#    NOT be touched. We tokenize into Arabic-script runs vs everything else,
#    reverse run order, reverse chars only inside Arabic runs, and mirror
#    brackets only on lines that actually contain Arabic (so Latin formulas
#    like "FG+(M+GEST)/2" are left alone).
# ---------------------------------------------------------------------------
ARABIC_RE = re.compile(r'[\u0600-\u06FF\uFB50-\uFEFF]+')
TOKEN_RE = re.compile(r'([\u0600-\u06FF\uFB50-\uFEFF]+|[^\u0600-\u06FF\uFB50-\uFEFF]+)')
BRACKET_ONLY_RE = re.compile(r'^[()\[\]]+$')
BRACKET_MAP = str.maketrans('()[]', ')(][')


def fix_line(line: str) -> str:
    # Reverse run order; reverse chars only inside Arabic runs; mirror a
    # bracket only when it stands alone as its own token (i.e. its partner
    # was separated from it by an Arabic run) -- brackets that stay bundled
    # together in one token (e.g. "(+)", "(M+GEST)") must NOT be mirrored.
    tokens = TOKEN_RE.findall(line)[::-1]
    out = []
    for tok in tokens:
        if ARABIC_RE.fullmatch(tok):
            out.append(tok[::-1])
        elif BRACKET_ONLY_RE.fullmatch(tok):
            out.append(tok.translate(BRACKET_MAP))
        else:
            out.append(tok)
    s = ''.join(out)
    s = re.sub(r'(\d)([\u0600-\u06FF])', r'\1 \2', s)  # digit/Arabic spacing
    return unicodedata.normalize('NFKC', s).strip()


def fix_cell(cell):
    if cell is None:
        return None
    cell = cell.strip()
    if cell == '':
        return None
    return '\n'.join(fix_line(l) for l in cell.split('\n') if l.strip() != '')


def parse_specializations(cell_text):
    if not cell_text:
        return []
    items = []
    for line in cell_text.split('\n'):
        line = line.strip().lstrip('-').strip()
        if line:
            items.append(line)
    return items


def parse_number(raw, kind):
    if raw is None or raw == '-':
        return None
    raw = raw.replace(',', '.').strip()
    try:
        return int(raw) if kind == 'int' else float(raw)
    except ValueError:
        return None  # leaves it out rather than crashing the whole run


# ---------------------------------------------------------------------------
# 2. Per-page domain header (the big colored title bar sits above the table
#    and is NOT part of the pdfplumber table, so it's pulled separately from
#    the words above the table's bounding box).
# ---------------------------------------------------------------------------
def get_domain_title(page, table):
    top = table.bbox[1]
    words = page.extract_words()
    above = [w['text'] for w in words if w['bottom'] <= top]
    if not above:
        return None
    return fix_line(' '.join(above))


# ---------------------------------------------------------------------------
# 3. Row classification + forward-fill merge logic
# ---------------------------------------------------------------------------
def is_data_row(row):
    cap = fix_cell(row[1])
    bac = fix_cell(row[3])
    if bac is None or cap is None:
        return False
    if not re.fullmatch(r'-|\d+', cap):
        return False
    if bac in ('نوع الباكالوريا',):
        return False
    return True


def extract():
    records = OrderedDict()  # code -> record
    current = {'domain': None, 'degree': None, 'institution': None,
               'specializations': [], 'code': None}

    with pdfplumber.open(PDF_PATH) as pdf:
        for page_index, page in enumerate(pdf.pages):
            page_num = page_index + 1
            if page_index == 0:
                continue  # cover page

            tables = page.find_tables()
            if not tables:
                continue
            table_obj = tables[0]
            rows = table_obj.extract()

            current['domain'] = get_domain_title(page, table_obj) or current['domain']

            for row in rows:
                if not is_data_row(row):
                    continue

                degree = fix_cell(row[7])
                institution = fix_cell(row[6])
                specializations_raw = fix_cell(row[5])
                code = fix_cell(row[4])
                bac_type = fix_cell(row[3])
                formula = fix_cell(row[2])
                capacity = parse_number(fix_cell(row[1]), 'int')
                last_score = parse_number(fix_cell(row[0]), 'float')

                if degree:
                    current['degree'] = degree
                if institution:
                    current['institution'] = institution
                if specializations_raw:
                    current['specializations'] = parse_specializations(specializations_raw)
                if code:
                    current['code'] = code

                key = current['code']
                if key not in records:
                    records[key] = {
                        'code': current['code'],
                        'domain': current['domain'],
                        'degree_track': current['degree'],
                        'institution': current['institution'],
                        'specializations': list(current['specializations']),
                        'admission_options': [],
                        'source_pages': [],
                    }
                rec = records[key]
                if page_num not in rec['source_pages']:
                    rec['source_pages'].append(page_num)
                rec['admission_options'].append({
                    'bac_type': bac_type,
                    'score_formula': formula,
                    'capacity': capacity,
                    'last_admitted_score_2025': last_score,
                })

    return list(records.values())


if __name__ == '__main__':
    data = extract()
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Total program records: {len(data)}")
    total_options = sum(len(r['admission_options']) for r in data)
    print(f"Total admission-option rows: {total_options}")
    domains = sorted(set(r['domain'] for r in data))
    print(f"Distinct domains: {len(domains)}")
    for d in domains:
        print(' -', d)

def process_pdf(pdf_path, output_path):
    global PDF_PATH
    global OUTPUT_PATH

    PDF_PATH = pdf_path
    OUTPUT_PATH = output_path

    data = extract()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "records": len(data),
        "output_file": output_path
    }