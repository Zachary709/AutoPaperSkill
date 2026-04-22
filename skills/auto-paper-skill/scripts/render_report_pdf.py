#!/usr/bin/env python3
"""Compile a Markdown paper report into PDF with XeLaTeX."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

IMAGE_RE = re.compile(r"!\[(.*?)\]\((.*?)\)")


def escape_latex(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    escaped = []
    for char in text:
        escaped.append(replacements.get(char, char))
    return "".join(escaped)


def markdown_to_latex(markdown: str, base_dir: Path) -> tuple[str, str]:
    title = "论文报告"
    body = []
    in_list = False

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            body.append(r"\end{itemize}")
            in_list = False

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("# "):
            close_list()
            title = line[2:].strip() or title
            continue
        if line.startswith("## "):
            close_list()
            body.append(rf"\section*{{{escape_latex(line[3:].strip())}}}")
            continue
        if line.startswith("### "):
            close_list()
            body.append(rf"\subsection*{{{escape_latex(line[4:].strip())}}}")
            continue

        image_match = IMAGE_RE.fullmatch(line)
        if image_match:
            close_list()
            alt_text, path_text = image_match.groups()
            image_path = Path(path_text)
            if not image_path.is_absolute():
                image_path = (base_dir / image_path).resolve()
            body.extend(
                [
                    r"\begin{figure}[H]",
                    r"\centering",
                    rf"\includegraphics[width=0.92\linewidth]{{\detokenize{{{image_path.as_posix()}}}}}",
                    rf"\caption*{{{escape_latex(alt_text)}}}",
                    r"\end{figure}",
                ]
            )
            continue

        if not line:
            close_list()
            body.append("")
            continue

        if line.startswith("- "):
            if not in_list:
                body.append(r"\begin{itemize}[leftmargin=*]")
                in_list = True
            body.append(rf"\item {escape_latex(line[2:].strip())}")
            continue

        close_list()
        body.append(escape_latex(line))

    close_list()
    return title, "\n".join(body)


def build_latex_document(markdown: str, base_dir: Path) -> str:
    title, body = markdown_to_latex(markdown, base_dir)
    return rf"""
\documentclass[12pt]{{ctexart}}
\usepackage{{fontspec}}
\usepackage{{xeCJK}}
\usepackage{{graphicx}}
\usepackage{{float}}
\usepackage{{geometry}}
\usepackage{{hyperref}}
\usepackage{{enumitem}}
\geometry{{a4paper,margin=1in}}
\setmainfont{{Noto Serif CJK SC}}
\setCJKmainfont{{Noto Serif CJK SC}}
\setlength{{\parskip}}{{0.5em}}
\setlength{{\parindent}}{{2em}}
\title{{{escape_latex(title)}}}
\author{{}}
\date{{}}
\begin{{document}}
\maketitle
{body}
\end{{document}}
""".strip() + "\n"


def render_markdown_file_to_pdf(markdown_file: Path, output_pdf: Path) -> Path:
    markdown = markdown_file.read_text(encoding="utf-8")
    latex = build_latex_document(markdown, markdown_file.parent)

    with tempfile.TemporaryDirectory(prefix="autopaper-report-", dir=str(output_pdf.parent)) as tmpdir:
        workdir = Path(tmpdir)
        tex_path = workdir / "report.tex"
        tex_path.write_text(latex, encoding="utf-8")

        subprocess.run(
            [
                "xelatex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-output-directory",
                str(workdir),
                str(tex_path),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        pdf_path = workdir / "report.pdf"
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, output_pdf)
    return output_pdf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile a Markdown paper report into PDF.")
    parser.add_argument("--markdown-file", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    render_markdown_file_to_pdf(Path(args.markdown_file), Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
