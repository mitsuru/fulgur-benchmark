"""
Generate test HTML documents dynamically.
No external dependencies, fully reproducible output.
"""

from __future__ import annotations

import os
import textwrap

# ---------------------------------------------------------------------------
# Shared content helpers
# ---------------------------------------------------------------------------

_PARAGRAPHS = [
    (
        "The swift advancement of computational systems has reshaped the landscape of "
        "modern information processing. Engineers and researchers continually seek novel "
        "approaches to optimise throughput while maintaining correctness and reliability "
        "across distributed environments."
    ),
    (
        "Quantitative analysis of benchmark results reveals consistent patterns in "
        "resource utilisation. Memory allocation strategies, cache coherence protocols, "
        "and scheduling algorithms each contribute measurable effects to the overall "
        "performance profile observed under sustained workloads."
    ),
    (
        "Documentation serves as the connective tissue between implementation details "
        "and end-user understanding. Precise, well-structured prose reduces the cognitive "
        "load on readers and accelerates the onboarding process for new contributors "
        "joining a technical project at any stage of its lifecycle."
    ),
    (
        "Iterative refinement of test suites ensures that regressions are caught early "
        "and that the intended behaviour of each component is verified in isolation as "
        "well as in concert with the broader system. Automated pipelines further reduce "
        "the latency between a change being introduced and its consequences being known."
    ),
    (
        "Structured data formats facilitate interoperability between heterogeneous "
        "systems. Standardised schemas, versioning conventions, and backward-compatibility "
        "guarantees form the foundation upon which long-lived integrations are safely "
        "constructed and maintained over extended periods."
    ),
]

_LIST_ITEMS = [
    "Initialise the configuration registry before spawning worker processes.",
    "Validate all external inputs against the canonical schema definition.",
    "Emit structured log entries at each significant state transition.",
    "Gracefully handle transient network failures with exponential back-off.",
    "Flush pending writes to durable storage prior to process termination.",
]

_TABLE_HEADERS = ["Identifier", "Category", "Value", "Status"]
_TABLE_ROWS = [
    ["ITEM-001", "Alpha", "482.7", "Active"],
    ["ITEM-002", "Beta", "319.1", "Pending"],
    ["ITEM-003", "Alpha", "750.0", "Active"],
    ["ITEM-004", "Gamma", "128.4", "Inactive"],
    ["ITEM-005", "Beta", "603.9", "Active"],
]

_SVG_COLORS = ["#4A90D9", "#E07B54", "#6ABF69", "#F5C842", "#9B59B6"]

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

_BASE_CSS = textwrap.dedent("""\
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: Georgia, 'Times New Roman', serif;
        font-size: 12pt;
        line-height: 1.6;
        color: #222;
        background: #fff;
        padding: 2cm;
        max-width: 21cm;
        margin: 0 auto;
    }
    h1 { font-size: 2em; margin-bottom: 0.6em; }
    h2 { font-size: 1.4em; margin-top: 1.2em; margin-bottom: 0.4em; border-bottom: 1px solid #ccc; padding-bottom: 0.2em; }
    p { margin-bottom: 0.8em; text-align: justify; }
    table { border-collapse: collapse; width: 100%; margin: 0.8em 0; font-size: 0.9em; }
    th, td { border: 1px solid #bbb; padding: 0.35em 0.6em; text-align: left; }
    th { background: #f0f0f0; font-weight: bold; }
    tr:nth-child(even) td { background: #fafafa; }
    ul { margin: 0.6em 0 0.8em 1.4em; }
    li { margin-bottom: 0.3em; }
    .page-section { page-break-after: always; padding-bottom: 1em; }
    .page-section:last-child { page-break-after: avoid; }
    .svg-placeholder { display: block; margin: 1em auto; }
""")

# ---------------------------------------------------------------------------
# Building-block renderers
# ---------------------------------------------------------------------------


def _html_table(headers: list[str], rows: list[list[str]]) -> str:
    th_cells = "".join(f"<th>{h}</th>" for h in headers)
    body_rows = ""
    for row in rows:
        td_cells = "".join(f"<td>{cell}</td>" for cell in row)
        body_rows += f"<tr>{td_cells}</tr>\n"
    return f"<table>\n<thead><tr>{th_cells}</tr></thead>\n<tbody>\n{body_rows}</tbody>\n</table>\n"


def _html_list(items: list[str]) -> str:
    li_tags = "".join(f"<li>{item}</li>\n" for item in items)
    return f"<ul>\n{li_tags}</ul>\n"


def _svg_placeholder(width: int, height: int, color: str, label: str) -> str:
    return (
        f'<svg class="svg-placeholder" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{label}">\n'
        f'  <rect width="100%" height="100%" fill="{color}" rx="4" ry="4"/>\n'
        f'  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" '
        f'fill="#fff" font-family="sans-serif" font-size="14">{label}</text>\n'
        f'</svg>\n'
    )


def _wrap_html(title: str, body: str) -> str:
    return textwrap.dedent(f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        </head>
        <body>
        {body}
        </body>
        </html>
        """)


# ---------------------------------------------------------------------------
# Document generators
# ---------------------------------------------------------------------------


def _build_small() -> str:
    paras = "".join(f"<p>{_PARAGRAPHS[i]}</p>\n" for i in range(4))
    body = f"<h1>Benchmark Document &mdash; Small</h1>\n{paras}"
    return _wrap_html("Benchmark Document - Small", body)


def _build_medium_section(index: int, *, last: bool = False) -> str:
    section_class = "page-section" + ("" if not last else " last-section")
    para = _PARAGRAPHS[index % len(_PARAGRAPHS)]
    table = _html_table(_TABLE_HEADERS, _TABLE_ROWS)
    lst = _html_list(_LIST_ITEMS)
    return (
        f'<div class="{section_class}">\n'
        f"<h2>Section {index + 1}: Topic {chr(65 + index % 26)}</h2>\n"
        f"<p>{para}</p>\n"
        f"{table}"
        f"{lst}"
        f"<p>Concluding remarks for section {index + 1}. "
        f"Refer to the table and list above for supporting details.</p>\n"
        f"</div>\n"
    )


def _build_medium() -> str:
    sections = "".join(
        _build_medium_section(i, last=(i == 9)) for i in range(10)
    )
    body = f"<h1>Benchmark Document &mdash; Medium</h1>\n{sections}"
    return _wrap_html("Benchmark Document - Medium", body)


def _build_large_section(index: int, *, last: bool = False) -> str:
    section_class = "page-section" + ("" if not last else " last-section")
    para = _PARAGRAPHS[index % len(_PARAGRAPHS)]
    table = _html_table(_TABLE_HEADERS, _TABLE_ROWS)
    lst = _html_list(_LIST_ITEMS)

    # Insert an SVG placeholder every 5 sections
    svg_block = ""
    if index % 5 == 0:
        color = _SVG_COLORS[(index // 5) % len(_SVG_COLORS)]
        label = f"Figure {index // 5 + 1}"
        svg_block = _svg_placeholder(480, 120, color, label)

    return (
        f'<div class="{section_class}">\n'
        f"<h2>Section {index + 1}: Topic {chr(65 + index % 26)}{index // 26 + 1}</h2>\n"
        f"<p>{para}</p>\n"
        f"{table}"
        f"{lst}"
        f"{svg_block}"
        f"<p>Concluding remarks for section {index + 1}.</p>\n"
        f"</div>\n"
    )


def _build_large() -> str:
    sections = "".join(
        _build_large_section(i, last=(i == 99)) for i in range(100)
    )
    body = f"<h1>Benchmark Document &mdash; Large</h1>\n{sections}"
    return _wrap_html("Benchmark Document - Large", body)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_BUILDERS: dict[str, object] = {
    "small": _build_small,
    "medium": _build_medium,
    "large": _build_large,
}


def generate_html(name: str, output_dir: str) -> str:
    """Generate an HTML benchmark document and write it to *output_dir*.

    Parameters
    ----------
    name:
        One of ``"small"``, ``"medium"``, or ``"large"``.
    output_dir:
        Directory in which the file will be written. Created if absent.

    Returns
    -------
    str
        Absolute path to the written file.

    Raises
    ------
    ValueError
        If *name* is not a recognised document type.
    """
    if name not in _BUILDERS:
        raise ValueError(
            f"Unknown document name {name!r}. "
            f"Expected one of: {', '.join(sorted(_BUILDERS))}."
        )
    os.makedirs(output_dir, exist_ok=True)
    html_content = _BUILDERS[name]()  # type: ignore[operator]
    file_path = os.path.abspath(os.path.join(output_dir, f"{name}.html"))
    with open(file_path, "w", encoding="utf-8") as fh:
        fh.write(html_content)
    return file_path


def generate_css(output_dir: str) -> str:
    """Write the shared CSS file and return its absolute path."""
    os.makedirs(output_dir, exist_ok=True)
    css_path = os.path.abspath(os.path.join(output_dir, "style.css"))
    with open(css_path, "w", encoding="utf-8") as fh:
        fh.write(_BASE_CSS)
    return css_path


def generate_all(output_dir: str) -> tuple[dict[str, str], str]:
    """Generate all benchmark documents and the shared CSS file.

    Parameters
    ----------
    output_dir:
        Directory in which files will be written. Created if absent.

    Returns
    -------
    tuple[dict[str, str], str]
        A tuple of (document mapping, css file path).
    """
    css_path = generate_css(output_dir)
    docs = {name: generate_html(name, output_dir) for name in _BUILDERS}
    return docs, css_path


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    default_output = os.path.join(os.path.dirname(__file__), "output")
    output_dir = sys.argv[1] if len(sys.argv) > 1 else default_output

    print(f"Generating benchmark HTML documents in: {os.path.abspath(output_dir)}")
    paths, css_path = generate_all(output_dir)
    print(f"  CSS:      {css_path}")
    for doc_name, doc_path in sorted(paths.items()):
        size_kb = os.path.getsize(doc_path) / 1024
        print(f"  {doc_name:<8}  {doc_path}  ({size_kb:.1f} KB)")
    print("Done.")
