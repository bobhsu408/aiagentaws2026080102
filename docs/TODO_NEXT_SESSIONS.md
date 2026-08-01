# 職涯導航家 — 待辦事項清單（按優先序）

> **2026-08-01 執行提示**：目前唯一正式執行順序以 `docs/IMPLEMENTATION_PLAN_20250731.md` 為準。Task 1 已完成；AgentCore Runtime 已額外先行部署並通過 invoke，但這只是部署檢查點，**不代表 Task 6 完成**。新 session 下一步必須從 **Task 2** 開始，完成每個 Task 後建立 `docs/reports/TASK_N_REPORT.md` 並 commit。
>
> 最後更新：2026-08-01
> 每項含預估工時、前置依賴、驗收標準

---

## 優先級說明

- **P0 — 比賽必須**：沒做完就無法 demo
- **P1 — 核心品質**：做完才不會被評審挑出明顯錯誤
- **P2 — 加分項**：提升評分但非致命
- **P3 — 技術債**：比賽後再處理

---

## P0：比賽必須

### T1. 解決前端接入（瀏覽器 → Agent）

| 項目 | 內容 |
|------|------|
| **預估工時** | 2~4 小時 |
| **前置依賴** | 無（獨立於資料層） |
| **描述** | 讓瀏覽器能發 HTTP 請求到 Agent 並收到回覆 |
| **建議方案** | Cognito Identity Pool 發臨時憑證 → 前端用 AWS SDK for JS 做 SigV4 簽名直接呼叫 AgentCore |
| **替代方案** | (A) 確認 Lambda Function URL + AWS_IAM auth + CloudFront OAC 的「建立」是否被擋；(B) 比賽當天新帳號若有 API Gateway 權限就用標準方案 |
| **驗收標準** | 瀏覽器打字 → 收到 Agent 六步驟完整回覆 |
| **相關檔案** | `proxy_lambda/app.py`, `deploy_proxy.sh`, `frontend/index.html`（不在此 repo） |
| **風險** | 帳號可能連 Cognito Identity Pool 都沒有（目前只確認有 `cognito-idp:*`，Identity Pool 是 `cognito-identity:*`） |
| **備註** | 這是目前唯一的致命卡點，比賽需要 demo 網頁 |

---

### T2. 修正 resources.json 關鍵錯誤（P0 等級的 2 筆）

| 項目 | 內容 |
|------|------|
| **預估工時** | 1 小時 |
| **前置依賴** | 無 |
| **描述** | 修正會誤導使用者的嚴重錯誤 |
| **具體內容** | (1) `training_living_allowance` 移除「可與失業給付併行」描述；(2) `mid_age_employment_subsidy` 標明是雇主獎助，修正金額或移除 |
| **驗收標準** | Agent 回覆中不再出現法律上錯誤的併領建議、不再告訴勞工「你每月可領 5000 元」 |
| **相關檔案** | `app/career_navigator/data/resources.json` |
| **參考** | `CURRENT_DATA_ISSUES.md` #2, #4 |

---

## P1：核心品質

### T3. 實作新版 resources.json（Schema 遷移 + 擴充）

| 項目 | 內容 |
|------|------|
| **預估工時** | 3~5 小時 |
| **前置依賴** | T2 完成（或直接跳過舊版，一步到位寫新版） |
| **描述** | 按 `RESOURCES_SCHEMA_PROPOSAL.md` 重寫全部資料，修正全部錯誤，新增缺漏項目 |
| **具體內容** | (1) 建立 `resources_v2.json`；(2) 修正既有 8 筆（含條件分支、法規引用）；(3) 新增 7 筆缺漏項目；(4) 新增 `constants.json`（最低工資等） |
| **目標筆數** | 15~22 筆 |
| **驗收標準** | 每筆有 `law_references`、金額可追溯到法條、`recipient` 明確 |
| **相關檔案** | `app/career_navigator/data/resources.json`, `RESOURCES_SCHEMA_PROPOSAL.md` |

---

### T4. 改寫 career_tools.py 適配新 schema

| 項目 | 內容 |
|------|------|
| **預估工時** | 2~3 小時 |
| **前置依賴** | T3（新 schema JSON 完成） |
| **描述** | `match_resources` 和 `calculate_benefit` 需適配新結構 |
| **具體改動** | (1) `match_resources`：新增 `recipient` 過濾；(2) `calculate_benefit`：讀 `benefit.base` + `conditional_tiers` + `surcharges`；(3) 回傳中加入 `law_references` 供 Agent 引用 |
| **驗收標準** | `agentcore invoke` 輸入測試案例 → 回覆金額正確、附法規條號 |
| **相關檔案** | `app/career_navigator/tools/career_tools.py` |

---

### T5. 寫法規擷取腳本

| 項目 | 內容 |
|------|------|
| **預估工時** | 2 小時 |
| **前置依賴** | T3（知道要擷取哪些欄位） |
| **描述** | Python 腳本：下載法規 API → 篩選目標法規 → 萃取條文中的金額/條件 → 輸出結構化 JSON |
| **用途** | (1) 產出 resources.json 的草稿（人工校驗後使用）；(2) 法規更新時可重跑 |
| **驗收標準** | 腳本跑一次可自動產出涵蓋 10+ 個補助方案的 JSON |
| **輸出位置** | `scripts/extract_laws.py`（建議新增） |

---

### T6. 端到端測試

| 項目 | 內容 |
|------|------|
| **預估工時** | 1 小時 |
| **前置依賴** | T1 + T4 完成 |
| **描述** | 瀏覽器 → API → Agent → 六步驟完整回覆，含金額正確性檢查 |
| **測試案例** | (1) 小明 35歲餐廳主管被裁員；(2) 55歲工廠女工育有幼兒；(3) 28歲身障者想轉職 |
| **驗收標準** | 3 個案例回覆金額與法規一致、不出現併領矛盾、有條號引用 |

---

## P2：加分項

### T7. 擴充資料至 25~30 筆（含第 2 層手動整理）

| 項目 | 內容 |
|------|------|
| **預估工時** | 3~4 小時 |
| **前置依賴** | T3 |
| **描述** | 手動整理行政計畫類方案（產業新尖兵、微型創業鳳凰、各縣市特有方案等） |
| **來源** | 台灣就業通網站、勞動力發展署官網、各分署公告 |
| **驗收標準** | 每筆有 `source_url`、`last_verified`、涵蓋至少 6 種 target_group |

---

### T8. Agent 回覆加入法規引用格式

| 項目 | 內容 |
|------|------|
| **預估工時** | 0.5 小時 |
| **前置依賴** | T4 |
| **描述** | 修改 system prompt，指示 Agent 在回覆金額時附上「依據 ○○法 第○條」 |
| **改動位置** | `app/career_navigator/main.py` 的 `DEFAULT_SYSTEM_PROMPT` |
| **驗收標準** | Agent 回覆中每個金額後面都有法規出處 |

---

### T9. 準備比賽帳號切換腳本

| 項目 | 內容 |
|------|------|
| **預估工時** | 1 小時 |
| **前置依賴** | 無 |
| **描述** | 寫一個 shell 腳本，拿到新帳號後快速確認可用服務 |
| **功能** | (1) `aws sts get-caller-identity`；(2) 試呼叫 Bedrock / Lambda / Cognito / S3 / EventBridge；(3) 輸出可用/不可用清單 |
| **輸出位置** | `scripts/check_permissions.sh`（建議新增） |

---

### T10. 前端部署到 S3 靜態網站

| 項目 | 內容 |
|------|------|
| **預估工時** | 1 小時 |
| **前置依賴** | T1（前端接入方案確定） |
| **描述** | `frontend/index.html` 部署到 S3，啟用靜態網站託管 |
| **驗收標準** | 有一個公開 URL 可開啟聊天頁面 |

---

### T11. 加入 2~3 個統計數據到 Agent 回覆

| 項目 | 內容 |
|------|------|
| **預估工時** | 0.5 小時 |
| **前置依賴** | 無 |
| **描述** | 在 system prompt 或 resources 中嵌入統計佐證（失業率、職訓預算執行率等），增加應用性評分 |
| **來源** | 主計總處、勞動統計查詢網 |

---

## P3：技術債（比賽後）

### T12. MCP Client 加 timeout + fallback

| 項目 | 內容 |
|------|------|
| **預估工時** | 1 小時 |
| **前置依賴** | 無 |
| **描述** | `mcp_client/client.py` 加 connection timeout、搜尋失敗時 graceful degradation |

---

### T13. Agent 快取加 LRU / TTL

| 項目 | 內容 |
|------|------|
| **預估工時** | 0.5 小時 |
| **前置依賴** | 無 |
| **描述** | `main.py` 的 `agent_factory()` cache 改用 `functools.lru_cache` 或加 TTL |

---

### T14. AgentCore Memory 啟用策略

| 項目 | 內容 |
|------|------|
| **預估工時** | 1 小時 |
| **前置依賴** | 無 |
| **描述** | `agentcore.json` 的 `strategies: []` 改為啟用 SEMANTIC 或 SUMMARIZATION |

---

### T15. 模型 fallback 機制

| 項目 | 內容 |
|------|------|
| **預估工時** | 1 小時 |
| **前置依賴** | 無 |
| **描述** | `model/load.py` 硬編碼 Claude Sonnet 4.5，加一個 fallback model（如 Haiku） |

---

### T16. streaming invocation 加 retry / timeout

| 項目 | 內容 |
|------|------|
| **預估工時** | 1 小時 |
| **前置依賴** | 無 |
| **描述** | `main.py` 的 `agent.stream_async()` 包一層 retry + timeout |

---

## 建議執行順序（比賽前）

```
T2（1hr）→ T3（3-5hr）→ T4（2-3hr）→ T5（2hr）
                                         ↓
T1（2-4hr，可與上面並行）→ T6（1hr）→ T10（1hr）
                                         ↓
                              T8（0.5hr）→ T9（1hr）→ T11（0.5hr）→ T7（3-4hr）
```

**最短路徑**（如果時間極有限）：T2 → T1 → T6 = 約 5~7 小時，可以 demo 出基本功能。

**完整路徑**：所有 P0+P1+P2 = 約 17~23 小時。

---

## 依賴關係圖

```
T1（前端接入）─────────────────────────────┐
                                           ├→ T6（端到端測試）→ T10（S3部署）
T2（修P0錯誤）→ T3（新schema）→ T4（改工具）┘
                      │
                      ├→ T5（擷取腳本）
                      ├→ T7（擴充資料）
                      └→ T8（法規引用格式）

T9（權限腳本）   — 獨立
T11（統計數據）  — 獨立
T12~T16（技術債）— 獨立，比賽後
```
