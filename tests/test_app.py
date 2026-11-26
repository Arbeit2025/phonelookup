import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app, classify, format_number, normalize


def test_normalize_hyphen():
    assert normalize("090-1234-5678") == "09012345678"


def test_normalize_fullwidth():
    assert normalize("０９０１２３４５６７８") == "09012345678"


def test_normalize_spaces_and_parens():
    assert normalize("(03) 1234 5678") == "0312345678"


def test_normalize_international():
    assert normalize("+81-90-1234-5678") == "09012345678"
    assert normalize("819012345678") == "09012345678"


def test_normalize_invalid():
    assert normalize("abcd") is None
    assert normalize("") is None


def test_classify_mobile():
    for head in ("070", "080", "090"):
        r = classify(head + "12345678")
        assert r["kind"] == "mobile"
        assert r["label"] == "携帯電話"


def test_classify_ip_phone():
    r = classify("05012345678")
    assert r["kind"] == "ip"


def test_classify_m2m():
    r = classify("02012345678")
    assert r["kind"] == "m2m"


def test_classify_freecall():
    assert classify("0120123456")["kind"] == "freecall"
    assert classify("0800123456")["kind"] == "freecall"


def test_classify_navi_has_warning():
    r = classify("0570123456")
    assert r["kind"] == "navi"
    assert r["warning"]


def test_classify_special():
    assert classify("0180123456")["kind"] == "special"
    assert classify("0990123456")["kind"] == "special"


def test_classify_landline_tokyo():
    r = classify("0312345678")
    assert r["kind"] == "landline"
    assert "東京" in r["area"]


def test_classify_landline_gunma():
    r = classify("0271234567")
    assert r["kind"] == "landline"
    assert "群馬" in r["area"]


def test_classify_landline_longest_prefix():
    # 0797 (宝塚・西宮) must win over 079 (姫路)
    r = classify("0797123456")
    assert "宝塚" in r["area"]
    # 0997 (奄美) must win over 099 (鹿児島)
    r = classify("0997123456")
    assert "奄美" in r["area"]


def test_classify_landline_unknown_area():
    r = classify("0999123456")
    assert r["kind"] == "landline"
    assert "鹿児島" in r["area"]  # falls back to 099


def test_classify_unknown():
    assert classify("12345")["kind"] == "unknown"
    assert classify(None)["kind"] == "unknown"
    assert classify("01112345678")["kind"] == "unknown"  # 11 digits, not mobile/ip/m2m


def test_format_number():
    assert format_number("09012345678", "mobile") == "090-1234-5678"
    assert format_number("05012345678", "ip") == "050-1234-5678"
    assert format_number("0120123456", "freecall") == "0120-123-456"
    assert format_number("0312345678", "landline") == "03-1234-5678"
    assert format_number("0111234567", "landline") == "011-123-4567"
    assert format_number("0422123456", "landline") == "0422-12-3456"
    assert format_number("0271234567", "landline") == "027-123-4567"


def test_index_get():
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200


def test_index_post_mobile():
    client = app.test_client()
    resp = client.post("/", data={"q": "090-1234-5678"})
    assert resp.status_code == 200
    assert "携帯電話" in resp.get_data(as_text=True)


def test_index_css_not_escaped():
    # render_template_string で CSS/JS を埋め込むとき |safe が無いと
    # 引用符がエスケープされて画面が壊れる事故の回帰テスト
    client = app.test_client()
    html = client.get("/").get_data(as_text=True)
    assert 'getElementById("f")' in html
    assert "&#34;" not in html
    assert "&#39;" not in html
