from flask import Flask, render_template, request, jsonify
import pandas as pd
import io
import re

app = Flask(__name__)

# 노드/슬롯 ID 정의 (이미지 구조 기준)
NODE_IDS = [
    ["A101", "A102", "A103", "A104", "A105", "A106"],
    ["A301", "A302", "A303", "A304", "A305", "A306"],
    ["A501", "A502", "A503", "A504", "A505", "A506"],
]
TOP_SLOTS = ["A201", "A202", "A203", "A204", "A205", "A206", "A207"]  # 상-중
BOT_SLOTS = ["A401", "A402", "A403", "A404", "A405", "A406", "A407"]  # 중-하

ALL_NODES = {x for row in NODE_IDS for x in row}
ALL_SLOTS = set(TOP_SLOTS + BOT_SLOTS)

def _clean_qty(q: str) -> str:
    if q is None:
        return ""
    q = str(q).strip()
    q = q.replace(",", "")
    return q

def parse_pasted_text(text: str):
    """
    붙여넣기 텍스트(탭/공백 구분)를 파싱해서
    nodes/slots dict로 반환
    """
    nodes = {k: {"item": "", "qty": ""} for k in ALL_NODES}
    slots = {k: {"item": "", "qty": ""} for k in ALL_SLOTS}

    if not text:
        return nodes, slots

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return nodes, slots

    # 헤더 감지 시 첫 줄 스킵
    start = 1 if re.search(r"(장치장|곡종|재고)", lines[0]) else 0

    for ln in lines[start:]:
        parts = re.split(r"\t+|\s{2,}|\s+", ln.strip())
        parts = [p for p in parts if p]
        if len(parts) < 3:
            continue

        loc = parts[0].strip()
        item = parts[1].strip()
        qty = _clean_qty("".join(parts[2:]))

        if loc in nodes:
            nodes[loc] = {"item": item, "qty": qty}
        elif loc in slots:
            slots[loc] = {"item": item, "qty": qty}

    return nodes, slots

def parse_excel(file_bytes: bytes):
    """
    과제 6번용: 엑셀 업로드(xlsx) 파싱.
    기대 컬럼: 장치장 / 곡종 / 재고량
    """
    nodes = {k: {"item": "", "qty": ""} for k in ALL_NODES}
    slots = {k: {"item": "", "qty": ""} for k in ALL_SLOTS}

    bio = io.BytesIO(file_bytes)
    df = pd.read_excel(bio)

    # 컬럼명 표준화 (혹시 공백/대소문자 차이)
    df.columns = [str(c).strip() for c in df.columns]

    # 안전하게 필요한 컬럼만 찾기
    col_loc = next((c for c in df.columns if "장치장" in c), None)
    col_item = next((c for c in df.columns if "곡종" in c), None)
    col_qty = next((c for c in df.columns if "재고" in c), None)

    if not (col_loc and col_item and col_qty):
        raise ValueError("엑셀 컬럼명이 필요 형식(장치장/곡종/재고량)이 아닙니다.")

    for _, row in df.iterrows():
        loc = str(row[col_loc]).strip()
        item = str(row[col_item]).strip()
        qty = _clean_qty(row[col_qty])

        if loc in nodes:
            nodes[loc] = {"item": item, "qty": qty}
        elif loc in slots:
            slots[loc] = {"item": item, "qty": qty}

    return nodes, slots

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/parse")
def api_parse():
    data = request.get_json(force=True)
    text = data.get("text", "")
    nodes, slots = parse_pasted_text(text)
    return jsonify({"nodes": nodes, "slots": slots})

@app.post("/api/upload")
def api_upload():
    """
    과제 6번 충족용(엑셀 업로드).
    실무 보안 때문에 숨기거나 막아도 됨.
    """
    if "file" not in request.files:
        return jsonify({"error": "file이 없습니다."}), 400
    f = request.files["file"]
    if not f.filename.lower().endswith((".xlsx", ".xls")):
        return jsonify({"error": "엑셀 파일만 업로드하세요."}), 400

    try:
        nodes, slots = parse_excel(f.read())
        return jsonify({"nodes": nodes, "slots": slots})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.get("/health")
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
