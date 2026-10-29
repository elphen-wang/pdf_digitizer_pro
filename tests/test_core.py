"""PDF 加载与路径命中的集成测试（需要 PyMuPDF）。"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from pdf_digitizer.core import PdfSource


@pytest.fixture()
def sample_pdf(tmp_path: Path) -> Path:
    path = tmp_path / "sample.pdf"
    document = fitz.open()
    page = document.new_page(width=200, height=200)
    page.draw_line(
        fitz.Point(50, 150), fitz.Point(150, 50), color=(0, 0, 0), width=2
    )
    document.save(path)
    document.close()
    return path


@pytest.mark.integration
def test_source_renders_page_at_requested_scale(sample_pdf: Path) -> None:
    source = PdfSource(sample_pdf, render_scale=2.0)
    try:
        assert source.width == pytest.approx(200)
        assert source.height == pytest.approx(200)
        assert source.image.size == (400, 400)
    finally:
        source.close()


@pytest.mark.integration
def test_find_path_hits_near_vertex(sample_pdf: Path) -> None:
    source = PdfSource(sample_pdf)
    try:
        assert source.find_path(150, 50, radius=5.0) is not None
    finally:
        source.close()


@pytest.mark.integration
def test_find_path_returns_none_outside_radius(sample_pdf: Path) -> None:
    source = PdfSource(sample_pdf)
    try:
        assert source.find_path(10, 190, radius=5.0) is None
    finally:
        source.close()


@pytest.mark.integration
def test_path_points_returns_line_endpoints(sample_pdf: Path) -> None:
    source = PdfSource(sample_pdf)
    try:
        path = source.find_path(150, 50, radius=5.0)
        assert path is not None
        points = source.path_points(path)
        assert (150.0, 50.0) in points
        assert (50.0, 150.0) in points
    finally:
        source.close()
