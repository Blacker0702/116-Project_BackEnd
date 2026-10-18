# jieba + SVM 模型訓練

> 訓練 PythonEnd 使用的「句子分類模型」：判斷使用者說的一句話，是否屬於**需要記錄的醫療／飲食內容**。輸出的 `svm+jieba.joblib` 由 PythonEnd（`Flask_5498.py`）載入使用。

---

## 模型在做什麼

二分類，輸入一句中文，輸出 SVM 分數：

| 類別 | 意義 | 範例 |
|------|------|------|
| `1` | 醫療／飲食（需要記錄） | 「昨天早上喝了一杯白開水」、「醫生說我有高血壓」、「前陣子得了帶狀皰疹」 |
| `0` | 日常（不需記錄） | 「剛剛去跑了八公里」、「GitHub 上傳失敗了」、「如果現在有一杯米漿就好了」 |

> 類別 `0` 也包含「想吃」「好不好」這類**尚未實際吃**或帶疑問的飲食相關句子，讓模型學會區分「已經發生的飲食／醫療事實」與一般的想法或提問。

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `jieba_svm.py` | 訓練、評估、輸出模型與圖表的主程式 |
| `database_1200.csv` | 訓練資料集 |
| `svm_jieba.joblib` | 訓練完成的模型 |
| `requirements_1.txt` | 訓練環境的套件版本紀錄（conda 匯出） |

## 資料集（`database_1200.csv`）

| 項目 | 內容 |
|------|------|
| 筆數 | 1200 筆，皆不重複 |
| 欄位 | `text`（句子）、`label`（0 或 1） |
| 類別比例 | 0：600 筆、1：600 筆（平衡） |
| 標註衝突 | 無（沒有同一句同時標 0 與 1） |

## 訓練流程

```text
讀取 CSV ▶ 清理與去重 ▶ 切分訓練／測試集 ▶ jieba 斷詞 + TF-IDF ▶ LinearSVC 訓練
   ▶ 評估（報告、5-fold × 10 交叉驗證、推論時間、錯判句）▶ 輸出模型與圖表
```

1. **資料處理**：移除空值、去除句子前後空白、檢查並列出標註衝突句、依句子去重。
2. **切分**：8:2 分為訓練集與測試集，依類別分層（`stratify`），`random_state=42`。
3. **模型**：以 `make_pipeline` 串接
   - `TfidfVectorizer`：使用 jieba 斷詞（`jieba_tokenizer`），詞組範圍 `ngram_range=(1, 2)`
   - `LinearSVC`：線性 SVM
4. **評估**：
   - 訓練／測試準確率與 Classification Report
   - 5-fold × 10 次重複的交叉驗證（macro F1、accuracy）
   - 單句推論平均時間（ms）
   - 列出測試集中的錯判句子
5. **輸出**：模型檔、混淆矩陣圖、UMAP 視覺化圖。

## 執行方式

### 1. 安裝套件

`requirements_1.txt` 沒有列出以下套件，需另外安裝：

```bash
pip install jieba matplotlib seaborn umap-learn
```

其餘（`scikit-learn`、`pandas`、`joblib` 等）請參考 `requirements_1.txt`。

### 2. 準備資料夾

程式會把輸出寫到 `jieba+svm/` 資料夾，請先建立，並把 `database_1200.csv` 放在程式同一層：

```bash
mkdir "jieba+svm"
```

### 3. 執行

```bash
python jieba_svm.py
```

### 輸出

| 檔案 | 說明 |
|------|------|
| `jieba+svm/svm+jieba.joblib` | 訓練完成的模型 |
| `jieba+svm/confusion_matrix.png` | 測試集混淆矩陣 |
| `jieba+svm/umap_visualization.png` | 測試集特徵的 UMAP 降維圖（紅：Class 0 日常、藍：Class 1 醫療／飲食） |

> 圖表的中文字型設定為 `Microsoft JhengHei`（Windows），其他系統請在程式開頭改成可用的中文字型。

## 評估結果

執行後請把終端機印出的數字填入：

| 指標 | 數值 |
|------|------|
| 訓練準確率 | |
| 測試準確率 | |
| 5-fold × 10 macro F1 | |
| 5-fold × 10 accuracy | |
| 單句推論時間（ms） | |

## 在 PythonEnd 使用模型

PythonEnd 以 `decision_function` 的分數判斷：**分數 > 0 → 類別 1（儲存）**，否則略過。詳見 PythonEnd 的 README。

使用時要注意：

- **檔名**：PythonEnd 預設讀取 `svm+jieba.joblib`，請將模型放在 PythonEnd 資料夾並使用此檔名（或用 `MODEL_PATH` 指定）。上傳的 `svm_jieba.joblib` 若要使用，需要改名。
- **切詞函式**：模型存檔時記錄了 `jieba_tokenizer`。載入端必須定義同名函式，並掛回 `__main__`，`Flask_5498.py` 已處理。更換模型時請維持函式名稱不變。
- **版本一致**：`requirements_1.txt` 顯示訓練環境為 Python 3.12、scikit-learn 1.9.1、numpy 2.5.3；PythonEnd 的 Dockerfile 目前是 Python 3.10，`requirements.txt` 的 scikit-learn 也只寫 `>=1.3.0`。版本不同時，joblib 載入可能失敗或出現警告，建議將 Dockerfile 與 `requirements.txt` 對齊訓練環境的版本。
