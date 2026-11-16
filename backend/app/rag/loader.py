"""多格式文史资料解析：txt / md / pdf / docx。"""
from __future__ import annotations

from pathlib import Path


def _read_plain(path: Path) -> str:
    for enc in ("utf-8", "gbk", "utf-16"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("读取 PDF 需要安装 pypdf：pip install pypdf") from exc
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _read_docx(path: Path) -> str:
    try:
        import docx
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("读取 docx 需要安装 python-docx：pip install python-docx") from exc
    document = docx.Document(str(path))
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.append("\t".join(cell.text for cell in row.cells))
    return "\n".join(parts)


def load_text(path: str | Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".markdown"}:
        text = _read_plain(path)
    elif suffix == ".pdf":
        text = _read_pdf(path)
    elif suffix == ".docx":
        text = _read_docx(path)
    else:
        raise ValueError(f"暂不支持的文件类型：{suffix}")
    # 规整空白，去掉页眉页脚式的空行堆叠
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()
