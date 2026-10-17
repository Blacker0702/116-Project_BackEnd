# 1. 使用官方輕量的 Python 3.10 映像檔
FROM python:3.10-slim

# 2. 設定容器內的工作目錄
WORKDIR /app

# 3. 把本地的 requirements.txt 複製進容器內
COPY requirements.txt .

# 4. 安裝 Python 相依套件
RUN pip install --no-cache-dir -r requirements.txt

# 5. 把剩下的程式碼全部複製進去
COPY . .

# 6. 容器啟動時預設執行的指令
CMD ["python", "Flask_dev.py"]