from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'docs' / 'current-state-vs-roadmap.md'
OUTPUT = ROOT / 'docs' / 'current-state-vs-roadmap.pdf'

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
LEFT = 54
TOP = 740
BOTTOM = 54
FONT_SIZE = 11
LEADING = 15
MAX_CHARS = 88


def escape_pdf_text(value: str) -> str:
    return value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def markdown_to_lines(markdown: str) -> list[str]:
    lines: list[str] = []
    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line:
            lines.append('')
            continue

        if line.startswith('# '):
            lines.append(line[2:].strip().upper())
            lines.append('')
            continue

        if line.startswith('## '):
            lines.append(line[3:].strip().upper())
            continue

        if line.startswith('### '):
            lines.append(line[4:].strip())
            continue

        if line.startswith('- '):
            wrapped = textwrap.wrap(
                line[2:].strip(),
                width=MAX_CHARS - 4,
                subsequent_indent='    ',
            )
            if wrapped:
                wrapped[0] = '- ' + wrapped[0]
                lines.extend(wrapped)
            else:
                lines.append('-')
            continue

        if len(line) > 3 and line[0].isdigit() and line[1:3] == '. ':
            lines.extend(textwrap.wrap(line, width=MAX_CHARS, subsequent_indent='   ') or [line])
            continue

        lines.extend(textwrap.wrap(line, width=MAX_CHARS) or [''])
    return lines


def paginate(lines: list[str]) -> list[list[str]]:
    pages: list[list[str]] = []
    current: list[str] = []
    y = TOP
    for line in lines:
        if y < BOTTOM:
            pages.append(current)
            current = []
            y = TOP
        current.append(line)
        y -= LEADING
    if current:
        pages.append(current)
    return pages


def build_stream(page_lines: list[str]) -> str:
    commands = ['BT', f'/F1 {FONT_SIZE} Tf']
    y = TOP
    for line in page_lines:
        commands.append(f'1 0 0 1 {LEFT} {y} Tm ({escape_pdf_text(line)}) Tj')
        y -= LEADING
    commands.append('ET')
    return '\n'.join(commands)


def make_pdf(pages: list[list[str]]) -> bytes:
    objects: list[bytes] = []

    def add_object(body: str) -> int:
        objects.append(body.encode('latin-1'))
        return len(objects)

    font_id = add_object('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    pages_tree_id = add_object('<< >>')
    page_ids: list[int] = []

    for page in pages:
        stream = build_stream(page)
        content_id = add_object(
            f"<< /Length {len(stream.encode('latin-1'))} >>\nstream\n{stream}\nendstream"
        )
        page_id = add_object(
            f"<< /Type /Page /Parent {pages_tree_id} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )
        page_ids.append(page_id)

    kids = ' '.join(f'{page_id} 0 R' for page_id in page_ids)
    objects[pages_tree_id - 1] = f'<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>'.encode('latin-1')
    catalog_id = add_object(f'<< /Type /Catalog /Pages {pages_tree_id} 0 R >>')

    pdf = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f'{index} 0 obj\n'.encode('latin-1'))
        pdf.extend(body)
        pdf.extend(b'\nendobj\n')

    xref_offset = len(pdf)
    pdf.extend(f'xref\n0 {len(objects) + 1}\n'.encode('latin-1'))
    pdf.extend(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        pdf.extend(f'{offset:010d} 00000 n \n'.encode('latin-1'))

    pdf.extend(
        (
            f'trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n'
            f'startxref\n{xref_offset}\n%%EOF\n'
        ).encode('latin-1')
    )
    return bytes(pdf)


def main() -> None:
    pages = paginate(markdown_to_lines(SOURCE.read_text(encoding='utf-8')))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(make_pdf(pages))
    print(OUTPUT)


if __name__ == '__main__':
    main()
