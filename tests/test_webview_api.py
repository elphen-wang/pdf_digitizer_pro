"""pywebview 后端 WebViewApi 的单元测试。"""

from __future__ import annotations

import base64
from pathlib import Path

import fitz
import pytest

from pdf_digitizer.webview.api import WebViewApi


@pytest.fixture()
def api_bundle(tmp_path: Path) -> tuple[WebViewApi, Path]:
    pdf_path = tmp_path / "chart.pdf"
    document = fitz.open()
    page = document.new_page(width=200, height=200)
    page.draw_line(fitz.Point(50, 150), fitz.Point(150, 50), width=2)
    document.save(pdf_path)
    document.close()

    export_path = tmp_path / "export.txt"
    api = WebViewApi(
        window_getter=lambda: None,
        open_dialog=lambda: str(pdf_path),
        save_dialog=lambda _name, _types: str(export_path),
    )
    yield api, export_path
    api.close()


def _calibrate(api: WebViewApi) -> None:
    assert api.open_pdf()["ok"] is True
    assert api.record_calibration(0, 0.25, 0.75, 0.0)["ok"] is True
    assert api.record_calibration(1, 0.75, 0.75, 100.0)["ok"] is True
    assert api.record_calibration(2, 0.25, 0.75, 0.0)["ok"] is True
    assert api.record_calibration(3, 0.25, 0.25, 100.0)["complete"] is True


@pytest.mark.unit
def test_open_pdf_returns_png_data_url(api_bundle: tuple[WebViewApi, Path]) -> None:
    api, _ = api_bundle
    result = api.open_pdf()

    assert result["ok"] is True
    assert result["error"] is None
    assert (result["width"], result["height"]) == (400, 400)
    assert result["image"].startswith("data:image/png;base64,")

    payload = result["image"].split(",", 1)[1]
    assert base64.b64decode(payload).startswith(b"\x89PNG\r\n\x1a\n")


@pytest.mark.unit
def test_open_pdf_cancel_is_not_an_error(tmp_path: Path) -> None:
    api = WebViewApi(open_dialog=lambda: None)
    result = api.open_pdf()
    assert result["ok"] is False
    assert result["error"] is None


@pytest.mark.unit
def test_record_calibration_requires_sequential_indices(
    api_bundle: tuple[WebViewApi, Path],
) -> None:
    api, _ = api_bundle
    api.open_pdf()

    assert api.record_calibration(1, 0.5, 0.5, 1.0)["ok"] is False
    first = api.record_calibration(0, 0.25, 0.75, 0.0)
    assert first == {"ok": True, "complete": False, "error": None}


@pytest.mark.unit
def test_pick_curve_maps_endpoints(api_bundle: tuple[WebViewApi, Path]) -> None:
    api, _ = api_bundle
    _calibrate(api)

    result = api.pick_curve(0.75, 0.25, False, False)

    assert result["ok"] is True
    assert len(result["points"]) == 2
    assert result["points"][0] == pytest.approx([0.0, 0.0])
    assert result["points"][1] == pytest.approx([100.0, 100.0])
    assert result["highlight"][0] == pytest.approx([0.25, 0.75])
    assert result["highlight"][1] == pytest.approx([0.75, 0.25])


@pytest.mark.unit
def test_pick_curve_requires_calibration(api_bundle: tuple[WebViewApi, Path]) -> None:
    api, _ = api_bundle
    api.open_pdf()
    assert api.pick_curve(0.5, 0.5, False, False)["error"] == "not_calibrated"


@pytest.mark.unit
def test_pick_curve_reports_missing_vector_data(
    api_bundle: tuple[WebViewApi, Path],
) -> None:
    api, _ = api_bundle
    _calibrate(api)
    result = api.pick_curve(0.05, 0.05, False, False)
    assert result["ok"] is False
    assert result["error"] == "no_curve"


@pytest.mark.unit
def test_reset_calibration_disables_pick(api_bundle: tuple[WebViewApi, Path]) -> None:
    api, _ = api_bundle
    _calibrate(api)
    api.reset_calibration()
    assert api.pick_curve(0.75, 0.25, False, False)["error"] == "not_calibrated"


@pytest.mark.unit
def test_process_data_filters_and_stride(api_bundle: tuple[WebViewApi, Path]) -> None:
    api, _ = api_bundle
    _calibrate(api)
    api.pick_curve(0.75, 0.25, False, False)

    assert api.process_data({})["total"] == 2
    assert api.process_data({"xmin": 50})["total"] == 1
    assert api.process_data({"step": 2})["total"] == 1
    assert api.process_data({"sort_col": 1, "desc": True})["rows"][0] == pytest.approx(
        [100.0, 100.0]
    )


@pytest.mark.unit
def test_copy_text_has_header_and_separator(api_bundle: tuple[WebViewApi, Path]) -> None:
    api, _ = api_bundle
    _calibrate(api)
    api.pick_curve(0.75, 0.25, False, False)

    lines = api.copy_text({}, "\t").splitlines()
    assert lines[0] == "X\tY"
    assert len(lines) == 3
    assert "," in api.copy_text({}, ",")


@pytest.mark.unit
def test_save_export_writes_file(api_bundle: tuple[WebViewApi, Path]) -> None:
    api, export_path = api_bundle
    _calibrate(api)
    api.pick_curve(0.75, 0.25, False, False)

    result = api.save_export({}, ",")

    assert result == {"ok": True, "error": None}
    assert export_path.exists()
    assert export_path.read_text(encoding="utf-8").splitlines()[0] == "X,Y"


@pytest.mark.unit
def test_get_strings_supports_both_languages(
    api_bundle: tuple[WebViewApi, Path],
) -> None:
    api, _ = api_bundle
    chinese = api.get_strings("CN")
    english = api.get_strings("EN")
    assert "打开" in chinese["btn_open"]
    assert "Open" in english["btn_open"]
