# Task 3 完成報告 — 六步驟 Career Tools

> 完成日期：2026-08-01
> 對應計畫：`docs/IMPLEMENTATION_PLAN_20250731.md` Task 3
> 前置：Task 1（基礎設施）、Task 2（resources.json / constants.json）

---

## 一、目標

完成 Agent 的核心六步驟工具，讓 `match_resources` / `calculate_benefit` 等
改讀 Task 2 的新 schema（`benefit.base` / `conditional_tiers` / `surcharges` /
`concurrency_rules`），取代原本的空殼骨架。

---

## 二、關鍵決策（與使用者確認後定案）

| 編號 | 議題 | 決策 |
|------|------|------|
| A1 | 兩套程式碼落差（`agent/` vs `app/careernav/`） | **統一以 `app/careernav/` 為唯一來源**。tools 拆模組 + 資料檔一起放此；`agent/` 標記 DEPRECATED。 |
| A2 | 課程資料 | 先整理 **3 筆**計畫層級課程（`courses.json`），即時開課清單留待 Exa MCP。 |
| A3 | 通知管道 | 暫無 LINE token，**先做展示用 email 純模擬**；`send_notification` 預留 `line_user_id` 擴充位，`.env.example` 加 LINE 欄位註解。 |
| B3 | 缺數值時的金額處理 | 回傳公式 + 標記 `needs_input`，**同時以基本工資代入作保守下限估算**並標 `assumption`。 |
| C1 | 測試 | 補 `tests/test_career_tools.py`，共 15 個測試。 |

---

## 三、產出檔案

### 程式碼（`app/careernav/`）

```
app/careernav/
├── main.py                     # 改為 import tools.career_tools（sys.path 保險 + 絕對 import）
├── data/
│   ├── resources.json          # 6 筆情境 A 補助資料（由 agent/data 搬入）
│   ├── constants.json          # 2026 基本工資等常數
│   └── courses.json            # 新增：3 筆計畫層級課程
├── tools/
│   ├── __init__.py             # 刻意不 import strands，方便測試
│   ├── career_tools.py         # 六個 @tool 薄封裝
│   ├── logic.py                # 純業務邏輯（不依賴 strands）
│   ├── data_loader.py          # 資料載入 + 模組快取
│   ├── formula.py              # ast 白名單公式/條件求值（不用 eval）
│   └── profile.py              # profile schema + 欄位對應表 + 啟發式萃取
└── tests/
    └── test_career_tools.py    # 15 個單元測試
```

### 架構決策：邏輯與封裝分離

`@tool` 裝飾器會包裝函式、且 strands 為部署環境才有的依賴。為了可測試性，
將**純業務邏輯抽到 `logic.py`（零 strands 依賴）**，`career_tools.py` 只做
`@tool` 薄封裝。單元測試直接測 `logic.py`，本機無需安裝 strands 即可跑。

---

## 四、六步驟實作重點

1. **analyze_profile**：啟發式關鍵字萃取（年齡、離職原因、就保年資、身障、
   眷屬人數、投保薪資等），回報 `missing_fields` 讓 Agent 主動追問。
2. **match_resources**：逐欄位比對 eligibility，四級 `match_status`
   （eligible / likely / needs_info / excluded）；預設只回勞工方案
   （`include_employer` 可開雇主方案）；彙整 `concurrency_warnings`。
3. **calculate_benefit**：`resolve_tier` + `apply_conditional_tiers`
   （如 45 歲以上失業給付延長為 9 個月）+ `compute_surcharges`（眷屬加給
   10%/人、上限 20%）；缺投保薪資時以基本工資作保守下限並標 `assumption`。
4. **generate_roadmap**：0～6 個月時間軸 + 決策點（失業給付 vs 全日制職訓
   擇一）；課程兩段式：`curated`（從 courses.json 依年齡/族群篩，自動排除
   限青年的產業新尖兵）+ `hint`（Exa MCP 即時搜尋關鍵字）。
5. **get_checklist**：跨方案文件去重，區分通用文件與各方案專用文件，附
   取得方式提示（標明為一般性指引）。
6. **send_notification**：展示模式模擬（`demo_mode: true`、`channel: email`），
   保留 `line_user_id` 供未來接 LINE Messaging API。

---

## 五、驗證結果

```
$ ~/careernav_venv/bin/python -m pytest tests/ -q
...............                                                          [100%]
15 passed in 0.07s
```

涵蓋：公式安全求值（含拒絕 `__import__` 等不安全語法）、情境 A profile 萃取、
資格匹配（失業給付符合、就保年資不足者排除、職訓津貼標 likely）、
金額試算（45 歲以上 9 個月、投保薪資 45,000 → 月領 27,000、眷屬加給 2 人
= 9,000）、缺投保薪資的保守估算、roadmap 決策點與課程年齡過濾、文件去重、
通知展示模式。

另以 strands 環境驗證 `@tool` 封裝與 import 鏈：
```
TOOL_REGISTRY size: 6
tool names: ['analyze_profile', 'match_resources', 'calculate_benefit',
             'generate_roadmap', 'get_checklist', 'send_notification']
```

---

## 六、已知限制與後續

- **資料僅涵蓋情境 A（6 筆）**：情境 B（雇主僱用中高齡）、情境 C（高齡者
  + 代理人操作）尚無資料，Task 8 端到端測試前需決定是否補齊。
- **課程即時性**：`courses.json` 僅計畫層級穩定資訊，實際梯次/報名截止需
  Task 5 的 Exa MCP 即時補充。
- **LINE 通知**：目前為 email 展示模擬，待取得 Channel Access Token 後可
  啟用真實推播。
- **部署尚未重跑**：本 Task 只改程式碼與資料，尚未執行 `agentcore deploy`
  重新打包（屬 Task 6 範圍）。
