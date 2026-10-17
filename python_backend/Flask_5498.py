"""
Flask_5498.py
功能：
    1. analyze_message()：前置疑問句過濾 + jieba+SVM 二分類
    2. save_note()      ：將 usr_sentence 存入 Docker PostgreSQL (port 5432) 的 diet_notes
"""

import os
import sys

import jieba
import joblib
import psycopg2

# ---------------------------------------------------------------------------
# 設定（可用環境變數覆寫）
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 模型與本檔放在同一資料夾
MODEL_PATH = os.getenv("MODEL_PATH", os.path.join(BASE_DIR, "svm+jieba.joblib"))

PG_CONFIG = {
    "host": os.getenv("PG_HOST", "localhost"),   # Flask 在本機跑 → localhost；Flask 也在 Docker → 填 container 名稱
    "port": int(os.getenv("PG_PORT", "5432")),
    "dbname": os.getenv("PG_DB", "nutrition"),
    "user": os.getenv("PG_USER", "agnet_ro"),
    "password": os.getenv("PG_PASSWORD", "CC6550"),
}

# diet_notes 資料表欄位（請依實際結構調整）
TABLE_NAME = "diet_notes"
NOTE_COLUMN = "note"        # 存放使用者句子的欄位名稱（待確認）
TIME_COLUMN = "eaten_at"    # 存入時間欄位

# 測試用固定時間；正式上線改成 datetime.now()
FIXED_TIME = "2026-10-01"

QUESTION_KEYWORDS = ['？', '?', '什麼', '啥', '嗎', '怎麼', '多少',
                     '好不好', '為何', '為什麼', '為甚麼']


# ---------------------------------------------------------------------------
# jieba 切詞器
# 訓練腳本把 jieba_tokenizer 存在 __main__ 底下，joblib.load 時 pickle 會去
# __main__ 找這個函式，所以必須同名定義，並在載入前掛回 __main__。
# ---------------------------------------------------------------------------
def jieba_tokenizer(text):
    return list(jieba.cut(text))


_model = None


def load_model():
    """載入模型（只載入一次）。"""
    global _model
    if _model is None:
        sys.modules["__main__"].jieba_tokenizer = jieba_tokenizer
        _model = joblib.load(MODEL_PATH)
    return _model


# ---------------------------------------------------------------------------
# 1. 語意分析
# ---------------------------------------------------------------------------
def is_question(usr_sentence):
    """前置條件：是否含疑問關鍵字。"""
    return any(keyword in usr_sentence for keyword in QUESTION_KEYWORDS)


def svm_score(usr_sentence):
    """SVM decision_function 分數（>0 偏向類別 1，不含疑問句過濾）。"""
    return float(load_model().decision_function([usr_sentence])[0])


def analyze_message(usr_sentence):
    """
    回傳 (should_store, reason, score)
        should_store : True 表示需存入資料庫
        reason       : 判斷說明
        score        : SVM 分數；前置條件攔截時為 None
    """
    if not usr_sentence or not usr_sentence.strip():
        return False, "空訊息不儲存", None

    # 前置條件：疑問句不儲存
    if is_question(usr_sentence):
        return False, "疑問句不儲存", None

    score = svm_score(usr_sentence)
    if score > 0:
        return True, "SVM 判斷需儲存", score
    return False, "SVM 判斷不存", score


# ---------------------------------------------------------------------------
# 2. 存入資料庫
# ---------------------------------------------------------------------------
def save_note(usr_sentence):
    """
    將句子寫入 diet_notes，存入時間使用 FIXED_TIME。
    成功回傳新資料列 id；失敗直接拋出例外，由呼叫端處理。
    """
    with psycopg2.connect(**PG_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"INSERT INTO {TABLE_NAME} ({NOTE_COLUMN}, {TIME_COLUMN}) "
                f"VALUES (%s, %s) RETURNING id",
                (usr_sentence, FIXED_TIME),
            )
            return cur.fetchone()[0]