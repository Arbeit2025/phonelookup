# phonelookup - 電話番号しらべ
# 入力された電話番号から、番号の種別（携帯／固定／IP電話／フリーダイヤル等）と
# 固定電話の市外局番の地域を表示し、公開検索へのリンクを案内する単一ファイルアプリ。
# 入力された番号は保存しない（サーバー側に記録を残さない）。
#
# Unit 1: データ（市外局番表・特殊番号）
# Unit 2: 番号の正規化
# Unit 3: 種別判定
# Unit 4: 表示整形
# Unit 5: 画面（HTML/CSS/JS）
# Unit 6: ルーティング

from flask import Flask, render_template_string, request

app = Flask(__name__)

# ---------------------------------------------------------------
# Unit 1: データ
# 主な市外局番 -> 地域。長い局番から優先して照合する（例: 0797 を 079 より先に見る）。
AREA_CODES = {
    "011": "北海道（札幌市など）",
    "0134": "北海道（小樽市など）",
    "0138": "北海道（函館市など）",
    "0154": "北海道（釧路市など）",
    "0155": "北海道（帯広市など）",
    "0166": "北海道（旭川市など）",
    "017": "青森県（青森市など）",
    "0172": "青森県（弘前市など）",
    "018": "秋田県（秋田市など）",
    "019": "岩手県（盛岡市など）",
    "022": "宮城県（仙台市など）",
    "023": "山形県（山形市など）",
    "024": "福島県（福島市・郡山市など）",
    "025": "新潟県（新潟市など）",
    "026": "長野県（長野市など）",
    "027": "群馬県（前橋市・高崎市など）",
    "028": "栃木県（宇都宮市など）",
    "029": "茨城県（水戸市・つくば市など）",
    "03": "東京都（23区など）",
    "042": "東京都（八王子市・町田市・立川市など多摩地域）",
    "0422": "東京都（武蔵野市・三鷹市など）",
    "043": "千葉県（千葉市など）",
    "044": "神奈川県（川崎市）",
    "045": "神奈川県（横浜市）",
    "046": "神奈川県（横須賀市・三浦市など）",
    "0465": "神奈川県（小田原市など）",
    "0466": "神奈川県（藤沢市）",
    "0467": "神奈川県（鎌倉市・逗子市）",
    "047": "千葉県（船橋市・市川市・松戸市など）",
    "048": "埼玉県（さいたま市・川口市など）",
    "049": "埼玉県（川越市など）",
    "052": "愛知県（名古屋市など）",
    "053": "静岡県（浜松市など）",
    "0532": "愛知県（豊橋市など）",
    "054": "静岡県（静岡市など）",
    "055": "山梨県（甲府市など）",
    "0564": "愛知県（岡崎市など）",
    "0565": "愛知県（豊田市など）",
    "058": "岐阜県（岐阜市など）",
    "059": "三重県（津市など）",
    "06": "大阪府（大阪市など）",
    "072": "大阪府（堺市・豊中市・茨木市など）",
    "073": "和歌山県（和歌山市など）",
    "075": "京都府（京都市など）",
    "076": "石川県（金沢市など）",
    "077": "滋賀県（大津市など）",
    "078": "兵庫県（神戸市）",
    "079": "兵庫県（姫路市など）",
    "0797": "兵庫県（宝塚市・西宮市など）",
    "082": "広島県（広島市など）",
    "083": "山口県（山口市・下関市など）",
    "084": "広島県（福山市など）",
    "0852": "島根県（松江市）",
    "0853": "島根県（出雲市）",
    "086": "岡山県（岡山市など）",
    "087": "香川県（高松市など）",
    "088": "徳島県・高知県（徳島市・高知市など）",
    "089": "愛媛県（松山市など）",
    "092": "福岡県（福岡市など）",
    "093": "福岡県（北九州市など）",
    "0942": "福岡県（久留米市など）",
    "095": "長崎県（長崎市など）",
    "0952": "佐賀県（佐賀市）",
    "096": "熊本県（熊本市など）",
    "097": "大分県（大分市など）",
    "098": "沖縄県（那覇市など）",
    "0985": "宮崎県（宮崎市）",
    "099": "鹿児島県（鹿児島市など）",
    "0997": "鹿児島県（奄美市など）",
}

# ---------------------------------------------------------------
# Unit 2: 番号の正規化
FULLWIDTH = str.maketrans("０１２３４５６７８９", "0123456789")


def normalize(raw):
    """入力文字列を国内表記の数字だけに直す。数字以外が残れば None。"""
    if raw is None:
        return None
    s = str(raw).translate(FULLWIDTH).strip()
    for ch in ("-", " ", "　", "(", ")", "（", "）"):
        s = s.replace(ch, "")
    if s.startswith("+81"):
        s = "0" + s[3:]
    elif s.startswith("81") and len(s) in (12, 13):
        # 国際表記で先頭の0が落ちた形（例: 819012345678）を国内表記へ
        s = "0" + s[2:]
    if not s.isdigit():
        return None
    return s


# ---------------------------------------------------------------
# Unit 3: 種別判定


def classify(digits):
    """数字列から種別・地域・注意を返す。判定できなければ kind='unknown'。"""
    result = {"kind": "unknown", "label": "判定できませんでした", "area": None,
              "note": None, "warning": None}
    if digits is None or not digits.startswith("0") or len(digits) not in (10, 11):
        result["note"] = "日本の電話番号は 0 から始まる10桁または11桁です。"
        return result

    head3 = digits[:3]
    head4 = digits[:4]

    if len(digits) == 11 and head3 in ("070", "080", "090"):
        result.update(kind="mobile", label="携帯電話")
        result["note"] = ("番号ポータビリティ（MNP）があるため、番号から現在の"
                          "契約キャリアは分かりません。070はPHSで使われることもあります。")
        return result
    if len(digits) == 11 and head3 == "050":
        result.update(kind="ip", label="IP電話（050）")
        result["note"] = "インターネット回線を使うIP電話の番号です。契約者の地域とは結びつきません。"
        return result
    if len(digits) == 11 and head3 == "020":
        result.update(kind="m2m", label="020番号（M2M等の専用番号）")
        result["note"] = "機械同士の通信（M2M）などに使われる専用番号帯です。一般の音声電話番号ではありません。"
        return result
    if len(digits) == 10 and head4 in ("0120", "0800"):
        result.update(kind="freecall", label="フリーダイヤル（着信課金）")
        result["note"] = "かける側に通話料はかかりません。企業や団体の受付窓口によく使われます。"
        return result
    if len(digits) == 10 and head4 == "0570":
        result.update(kind="navi", label="ナビダイヤル（0570）")
        result["note"] = "企業や団体の代表窓口によく使われます。"
        result["warning"] = "ナビダイヤルは発信者に通話料がかかります。携帯のかけ放題プランの対象外になることが多い番号です。"
        return result
    if len(digits) == 10 and head4 == "0180":
        result.update(kind="special", label="0180番号（テレドーム等の特殊サービス）")
        result["warning"] = "情報料などがかかるサービスに使われることがある番号帯です。心当たりがなければかけ直さないでください。"
        return result
    if len(digits) == 10 and head4 == "0990":
        result.update(kind="special", label="0990番号（有料情報サービス系の番号帯）")
        result["warning"] = "有料情報サービスに使われてきた番号帯です。心当たりがなければかけ直さないでください。"
        return result

    if len(digits) == 10:
        for code in sorted(AREA_CODES, key=len, reverse=True):
            if digits.startswith(code):
                result.update(kind="landline", label="固定電話", area=AREA_CODES[code])
                result["note"] = f"市外局番 {code} の地域の固定電話です。"
                return result
        result.update(kind="landline", label="固定電話")
        result["note"] = "固定電話のようですが、市外局番がこのツールの収録表にありませんでした。"
        return result

    result["note"] = "10桁・11桁の既知の番号帯に当てはまりませんでした。"
    return result


# ---------------------------------------------------------------
# Unit 4: 表示整形


def format_number(digits, kind):
    """読みやすいハイフン区切りにする。"""
    if digits is None:
        return ""
    if kind in ("mobile", "ip", "m2m") and len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if kind in ("freecall", "navi", "special") and len(digits) == 10:
        return f"{digits[:4]}-{digits[4:7]}-{digits[7:]}"
    if kind == "landline" and len(digits) == 10:
        for code in sorted(AREA_CODES, key=len, reverse=True):
            if digits.startswith(code):
                rest = digits[len(code):]
                if len(rest) == 8:
                    return f"{code}-{rest[:4]}-{rest[4:]}"
                if len(rest) == 7:
                    return f"{code}-{rest[:3]}-{rest[3:]}"
                if len(rest) == 6:
                    return f"{code}-{rest[:2]}-{rest[2:]}"
        return f"{digits[:4]}-{digits[4:7]}-{digits[7:]}"
    return digits


# ---------------------------------------------------------------
# Unit 5: 画面
CSS = """
* { box-sizing: border-box; }
body { margin: 0; font-family: sans-serif; background: #f4f6f8; color: #222; }
main { max-width: 640px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 24px; margin: 8px 0 4px; }
.sub { color: #555; font-size: 14px; margin: 0 0 20px; }
form { display: flex; gap: 8px; }
input[type=text] { flex: 1; font-size: 18px; padding: 12px; border: 1px solid #bbb; border-radius: 8px; min-width: 0; }
button { font-size: 16px; padding: 12px 18px; border: 0; border-radius: 8px; background: #2563eb; color: #fff; cursor: pointer; }
.card { background: #fff; border: 1px solid #ddd; border-radius: 10px; padding: 16px; margin-top: 20px; }
.card h2 { margin: 0 0 6px; font-size: 20px; }
.num { font-size: 22px; letter-spacing: 1px; margin: 2px 0 8px; }
.area { font-size: 16px; margin: 4px 0; }
.note { color: #444; font-size: 14px; line-height: 1.6; }
.warn { background: #fff4e5; border: 1px solid #f0c36d; border-radius: 8px; padding: 10px 12px; font-size: 14px; line-height: 1.6; margin-top: 10px; }
.links { margin-top: 12px; font-size: 14px; line-height: 2; }
.links a { color: #2563eb; }
section { margin-top: 28px; font-size: 14px; line-height: 1.7; color: #333; }
section h3 { font-size: 16px; margin: 0 0 6px; }
footer { margin-top: 32px; font-size: 12px; color: #777; }
"""

SCRIPT = """
document.getElementById("f").addEventListener("submit", function () {
  var v = document.getElementById("q").value;
  document.getElementById("q").value = v.trim();
});
"""

PAGE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>電話番号しらべ phonelookup</title>
<style>{{ css|safe }}</style>
</head>
<body>
<main>
<h1>電話番号しらべ</h1>
<p class="sub">番号を入れると、種別（携帯・固定・IP電話・フリーダイヤルなど）と、固定電話なら市外局番の地域が分かります。</p>
<form id="f" method="post" action="/">
<input type="text" id="q" name="q" inputmode="tel" placeholder="例: 090-1234-5678" value="{{ query }}">
<button type="submit">調べる</button>
</form>
{% if result %}
<div class="card">
<h2>{{ result.label }}</h2>
<p class="num">{{ formatted }}</p>
{% if result.area %}<p class="area">地域：{{ result.area }}</p>{% endif %}
{% if result.note %}<p class="note">{{ result.note }}</p>{% endif %}
{% if result.warning %}<p class="warn">{{ result.warning }}</p>{% endif %}
{% if digits %}
<p class="links">
この番号をWebで検索する：
<a href="https://www.google.com/search?q=%22{{ digits }}%22" target="_blank" rel="noopener">Googleで検索</a> /
<a href="https://www.bing.com/search?q={{ digits }}" target="_blank" rel="noopener">Bingで検索</a><br>
企業の窓口番号などは、検索結果から公式サイトで確認するのが確実です。
</p>
{% endif %}
</div>
{% endif %}
<section>
<h3>このツールで分かること・分からないこと</h3>
<p>分かるのは「番号そのものの情報」だけです。個人の携帯電話や固定電話について、契約者の名前や住所を調べられる公式のデータベースは存在しないため、このツールでも表示できません。番号の持ち主を名乗る相手がいても、番号だけで本人確認にはならない点に注意してください。</p>
<p>入力した番号は保存しません。判定はこのページの表示のためだけに使われます。</p>
</section>
<footer>phonelookup - 電話番号の種別と地域を調べる小さなツール</footer>
</main>
<script>{{ script|safe }}</script>
</body>
</html>
"""

# ---------------------------------------------------------------
# Unit 6: ルーティング


@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    formatted = ""
    digits = None
    query = ""
    if request.method == "POST":
        query = request.form.get("q", "")
        digits = normalize(query)
        result = classify(digits)
        formatted = format_number(digits, result["kind"]) if digits else ""
        if digits is None:
            digits = None
    return render_template_string(
        PAGE, css=CSS, script=SCRIPT, result=result,
        formatted=formatted, digits=digits, query=query,
    )


@app.route("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
