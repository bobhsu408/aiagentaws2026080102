# 程式碼規範

## Python

- 使用 Python 3.12+
- 所有函式加 type hints
- docstring 使用 Google style
- import 排序：標準庫 → 第三方 → 本地模組，各組間空一行
- 變數/函式用 snake_case，類別用 PascalCase
- 每個模組頂部加一行描述

## 爬蟲模組（scraper/）

- 新來源必須繼承 `BaseScraper`
- 可變的選擇器/URL 放 `config.py`，不硬編碼在邏輯中
- 爬蟲加適當延遲（預設 2 秒/頁），尊重目標站台
- 輸出統一使用 `models.py` 定義的資料結構

## 資料品質

- 每筆補助資料必須有：
  - `law_references`：法規條號 + 條文 URL
  - `recipient`：明確標示對象（勞工/雇主）
  - `source_url`：資料來源連結
  - `last_verified`：最後確認日期
- 金額不用字串，用結構化欄位（base / formula / conditional_tiers）

## Git

- commit message 用中文，格式：`類別: 簡述`
  - 類別：feat / fix / docs / refactor / chore
  - 例：`feat: 新增法規擷取腳本`
- 不提交 `output/` 目錄的擷取結果
- `.env` 和含 credentials 的檔案不入版本控制
