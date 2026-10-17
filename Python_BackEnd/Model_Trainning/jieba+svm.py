# 含 jieba 切詞、SVM 訓練+混淆矩陣+ UMAP 視覺化輸出 (模組化版本)

import time
import pandas as pd
import joblib
import jieba
import matplotlib.pyplot as plt
import seaborn as sns
import umap

from sklearn.model_selection import train_test_split, cross_val_score, RepeatedStratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import make_pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC

# 設定 Matplotlib 中文字型顯示
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'Arial Unicode MS', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

database_path = "database_1200.csv"

OUT_PATH = "jieba+svm/svm+jieba.joblib"
CM_OUT = "jieba+svm/confusion_matrix.png"
UMAP_OUT = "jieba+svm/umap_visualization.png"


def jieba_tokenizer(text):
    """定義 jieba 切詞器"""
    return list(jieba.cut(text))


def build_pipeline():
    """建立包含 jieba 切詞與 LinearSVC 的模型管道"""
    return make_pipeline(
        TfidfVectorizer(tokenizer=jieba_tokenizer, token_pattern=None, ngram_range=(1, 2)),
        LinearSVC()
    )


def train_and_eval(data_path, save_model_path=None):
    """
    模型訓練與評估函式
    回傳: model, X_test, y_test, pred_test
    """
    # 讀取資料集
    df = pd.read_csv(data_path, header=0, encoding="utf-8-sig")
    df = df.dropna()
    df["text"] = df["text"].astype(str).str.strip()
    df["label"] = df["label"].astype(int)

    print("原始筆數:", len(df), "| 不重複句數:", df["text"].nunique())

    # 檢查標註衝突
    conf = df.groupby("text")["label"].nunique()
    conflict = conf[conf > 1].index.tolist()
    print("標註衝突句數（同一句同時有 0 和 1）:", len(conflict))
    for s in conflict:
        print("  衝突:", s)

    # 去重
    d = df.drop_duplicates(subset="text")
    print("\n去重後各類句數:\n", d["label"].value_counts())
    X, y = d["text"], d["label"]

    # 切分訓練集與測試集
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    # 訓練模型
    model = build_pipeline().fit(Xtr, ytr)
    pred = model.predict(Xte)

    print("\ntrain acc:", round(model.score(Xtr, ytr), 4), "| test acc:", round(model.score(Xte, yte), 4),
          "| 測試集句數:", len(yte))
    print("\n[ Classification Report ]")
    print(classification_report(yte, pred, digits=3))

    # K-Fold 交叉驗證
    print("執行 5-fold x10 交叉驗證中...")
    cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=10, random_state=42)
    f1 = cross_val_score(build_pipeline(), X, y, cv=cv, scoring="f1_macro")
    acc = cross_val_score(build_pipeline(), X, y, cv=cv, scoring="accuracy")
    print("5-fold x10 macro F1: %.3f +/- %.3f | accuracy: %.3f +/- %.3f" % (f1.mean(), f1.std(), acc.mean(), acc.std()))

    # 計算單句推論時間
    t = time.perf_counter()
    for s in Xte.iloc[:100]:
        model.predict([s])
    print("單句推論平均 (ms): %.2f" % ((time.perf_counter() - t) / min(100, len(Xte)) * 1000))

    # 印出錯判句子
    bad = Xte[pred != yte]
    print("\n錯判句子:")
    for s, p, a in zip(bad, pred[pred != yte], yte[pred != yte]):
        print(f"  預測={p} 實際={a} | {s}")

    # 儲存模型
    if save_model_path:
        joblib.dump(model, save_model_path)
        print(f"\n模型已儲存至 {save_model_path}")

    return model, Xte, yte, pred


def plot_confusion_matrix(yte, pred, classes, save_path=CM_OUT):
    """
    生成並儲存混淆矩陣圖
    """
    cm = confusion_matrix(yte, pred)
    print("\nConfusion Matrix:\n", cm)

    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False,
                xticklabels=classes, yticklabels=classes)
    plt.xlabel("Predicted Label")
    plt.ylabel("True Label")
    plt.title("Confusion Matrix (with Jieba)")
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"混淆矩陣圖已儲存至 {save_path}")


def plot_umap(model, Xte, yte, save_path=UMAP_OUT):
    print("\n正在計算 UMAP 降維圖...")
    vectorizer = model.named_steps['tfidfvectorizer']
    Xte_tfidf = vectorizer.transform(Xte)

    reducer = umap.UMAP(n_neighbors=15, min_dist=0.1, random_state=42)
    embedding = reducer.fit_transform(Xte_tfidf)

    plt.figure(figsize=(8, 6))
    
    # 分開畫 0 與 1，自動產生漂亮的 Legend
    for label, color, name in zip([0, 1], ['#d62728', '#1f77b4'], ['Class 0 (日常)', 'Class 1 (醫療/飲食)']):
        mask = (yte == label)
        plt.scatter(
            embedding[mask, 0], embedding[mask, 1],
            c=color, label=name, alpha=0.7, s=25
        )

    plt.legend(loc='best')
    plt.title("UMAP Visualization of Test Set Features (with Jieba)")
    plt.xlabel("UMAP Dimension 1")
    plt.ylabel("UMAP Dimension 2")
    plt.tight_layout()
    plt.savefig(save_path, dpi=300)
    plt.close()
    print(f"UMAP 視覺化圖已儲存至 {save_path}")


if __name__ == "__main__":
    # 1. 訓練模型與評估
    model, Xte, yte, pred = train_and_eval(database_path, save_model_path=OUT_PATH)

    # 2. 繪製混淆矩陣圖
    plot_confusion_matrix(yte, pred, classes=model.classes_, save_path=CM_OUT)

    # 3. 繪製 UMAP 視覺化圖
    plot_umap(model, Xte, yte, save_path=UMAP_OUT)
