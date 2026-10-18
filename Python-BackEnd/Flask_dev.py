"""
Flask_dev.py
Flask 傳輸層 (port 5000)：接收 n8n 傳來的句子，交給 Flask_5498 判斷，
回報信心分數與是否存入。

n8n HTTP Request 節點設定：
    Method : POST
    URL    : http://host.docker.internal:5000/process
    Body   : JSON → {"usr_sentence": "..."}（也接受 "text" 欄位）

外部介入
curl -i -X POST http://localhost:5000/health

"""

from flask import Flask, jsonify, request

import Flask_5498

app = Flask(__name__)
app.json.ensure_ascii = False  # 回傳 JSON 保留中文


@app.route("/health", methods=["GET", "POST"])
def health():
    return jsonify({"status": "ok"})

@app.route('/process', methods=['POST'])
def process():
    data = request.get_json(silent=True) or {}
    usr_sentence = (data.get("usr_sentence") or data.get("text") or "").strip()

    if not usr_sentence:
        return jsonify({"status": "error", "message": "沒有收到文字"}), 400

    should_store, reason, score = Flask_5498.analyze_message(usr_sentence)
    rounded = round(score, 3) if score is not None else None

    if not should_store:
        return jsonify({"status": "skipped", "stored": False, "score": rounded,
                        "message": reason}), 200

    try:
        new_id = Flask_5498.save_note(usr_sentence)
    except Exception as e:
        return jsonify({"status": "error", "message": f"寫入資料庫失敗: {e}"}), 500

    return jsonify({"status": "ok", "stored": True, "id": new_id,
                    "score": rounded, "eaten_at": Flask_5498.FIXED_TIME}), 200


@app.route('/svm_test', methods=['POST'])
def svm_test():
    """只測試 SVM 判斷，不寫入資料庫。回傳疑問句過濾結果與 SVM 原始分數。"""
    data = request.get_json(silent=True) or {}
    usr_sentence = (data.get("usr_sentence") or data.get("text") or "").strip()

    if not usr_sentence:
        return jsonify({"status": "error", "message": "沒有收到文字"}), 400

    question = Flask_5498.is_question(usr_sentence)
    score = Flask_5498.svm_score(usr_sentence)

    return jsonify({
        "status": "ok",
        "text": usr_sentence,
        "is_question": question,            # True → 正式流程會被前置條件攔截
        "score": round(score, 3),           # SVM 原始分數（不受疑問句過濾影響）
        "svm_label": 1 if score > 0 else 0,
        "would_store": (not question) and score > 0,
        "stored": False,                    # 此路由永遠不寫入資料庫
    }), 200


if __name__ == "__main__":
    Flask_5498.load_model()   # 啟動時先載入模型，避免第一次請求延遲
    app.run(host="0.0.0.0", port=5000, debug=False)