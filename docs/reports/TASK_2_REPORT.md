# Task 2 完成報告：實作 resources.json 與 constants.json

> 完成日期：2026-08-01
> 執行者：Kiro AI

---

## 範圍調整說明（重要）

原計畫（`docs/IMPLEMENTATION_PLAN_20250731.md` 初版）要求 15~20 筆補助資料，走「求全」路線。經與使用者討論後改為 **MVP 情境反推法**：

1. 比賽主題是「因應高齡化的人力結構與人力發展」分析，原先設計的三個測試案例（餐廳主管被裁員／工廠女工育幼／身障者轉職）偏泛用，沒有對準高齡化主軸。
2. 重新規劃三個情境，聚焦人力結構轉銜：
   - **情境 A**：58 歲工廠作業員，產線自動化被資遣，距退休 7 年，體力已無法再做同類工作 → 技能斷層與轉銜
   - **情境 B**（未實作）：小型工廠雇主想僱用中高齡被裁員者，關注僱用成本 → 企業端人力發展
   - **情境 C**（未實作）：62 歲高齡者由子女代為操作系統查詢 → 高齡者再就業 + 介面可及性
3. 本次 Task 2 **只完成情境 A** 所需資料，其餘情境待後續 session 或子代理平行擴充。

**結果**：`resources.json` 從原訂 15~20 筆縮減為 **6 筆**，但每筆都直接對應情境 A 的實際決策點，不含用不到的資料膨脹體積。

---

## 產出

### 1. `agent/data/resources.json`（6 筆）

| id | 名稱 | recipient | 對應情境 A 的角色 |
|---|---|---|---|
| `unemployment_benefit` | 失業給付 | 勞工 | 基本生活支撐，45 歲以上最長 9 個月 |
| `training_living_allowance` | 職業訓練生活津貼 | 勞工 | 技能轉銜核心工具，含正確的併領限制 |
| `early_reemployment_bonus` | 提早就業獎助津貼 | 勞工 | 提早轉職成功的獎勵機制 |
| `relocation_transport_subsidy` | 異地就業交通補助金 | 勞工 | 跨區就業的通勤成本支持 |
| `relocation_moving_subsidy` | 搬遷補助金 | 勞工 | 跨區就業需搬遷時的一次性補助 |
| `relocation_rent_subsidy` | 租屋補助金 | 勞工 | 跨區就業租屋的長期補助 |

每筆均含：`law_references`（法規名稱+條號+URL）、`recipient`、`eligibility`、`benefit`（`base`/`conditional_tiers`/`surcharges`）、`concurrency_rules`、`required_documents`、`last_verified: "2026-08-01"`。

### 2. `agent/data/constants.json`

```json
{
  "year": 2026,
  "monthly_min_wage": 29500,
  "hourly_min_wage": 196,
  "min_wage_effective_date": "2026-01-01",
  ...
}
```

2026 年（民國 115 年）基本工資由 28,590 元調整為 29,500 元（時薪 196 元），來源：勞動部公告，經 web search 交叉確認（`mol.gov.tw` 英文版大事紀 PDF）。

---

## 資料來源與處理流程

### 問題：Python `urllib`/`requests` 無法下載法規 API

`scraper/laws/scraper.py` 原用 `urllib.request.urlopen()` 直接下載，在本機 Python 3.14 環境出現：

```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED]
certificate verify failed: Missing Subject Key Identifier
```

`curl` 對同一 URL 下載正常，確認是 Python 3.14 `ssl` 模組對此網站憑證的驗證比舊版更嚴格（憑證缺少 Subject Key Identifier 擴充欄位），非網路或程式邏輯問題。

**解法**：用 `curl` 下載兩個 ZIP 到 `output/`（法律 6MB、命令 25MB），寫一次性腳本 `output/run_local_extract.py`，將 `LawsScraper._download_and_parse` 的下載步驟替換為讀取本地檔案，其餘解析/篩選/萃取邏輯完全沿用既有 `scraper/laws/scraper.py`，不修改正式程式碼。

執行結果：擷取 14 部法規、75 條含金額關鍵字的條文，輸出至 `output/laws_extracted.json`（327 KB）。`output/` 已在 `.gitignore` 排除，不會進版控。

### 逐條核對法規原文

用 `output/get_article.py` 查詢工具，逐條讀取以下法規原文，確認 `resources.json` 中每個數字與條件都可追溯：

- 就業保險法 §11、§16、§18、§19、§19-1
- 就業促進津貼實施辦法 §18、§20、§26
- 就業保險促進就業實施辦法 §28、§31、§34

### 修正的舊資料錯誤

對照 `docs/CURRENT_DATA_ISSUES.md`：

- **`training_living_allowance`**：舊資料描述「可與失業給付併行申請不同期間」，法規原文（就業促進津貼實施辦法 §26 第 3 項）明確規定「請領失業給付期間不得同時請領本津貼」。新版已在 `concurrency_rules` 中正確標示，並在 `notes` 說明修正。
- **`unemployment_benefit` 的 `min_insurance_months`**：舊資料錯誤設為 1，正確值為 12（就業保險法 §11 第 1 項：前三年內年資合計滿一年）。新版已修正。
- **眷屬加給**：舊資料完全遺漏，新版依 §19-1 補上（每人 10%，上限 20%）。

---

## 驗收結果

執行驗證腳本（格式、必填欄位、id 唯一性、`concurrency_rules` 交叉引用）：

```
resources.json: 6 筆
=== 格式與交互引用檢查全部通過 ===
```

檢查項目：
- ✅ 每筆均有 `law_references`、`recipient`、`last_verified`
- ✅ 金額欄位為結構化資料（`amount_type` + `formula`/`fixed_amount`/`range`），無字串金額
- ✅ `recipient` 值僅限「勞工」/「雇主」/「事業單位」，本批全數為「勞工」（情境 A 為勞工視角，雇主端補助留待情境 B）
- ✅ `concurrency_rules` 中引用的 `conflicting_resource_id` 均存在於檔案內
- ✅ 無 `CURRENT_DATA_ISSUES.md` 列出的錯誤重現

---

## 尚未完成 / 後續事項

1. **情境 B、C 尚未建立對應資料**：中高齡僱用獎助（雇主端）、健保費補助、身心障礙職務再設計等，待後續 Task 或子代理平行查證後補充。
2. **第 2 層行政計畫資料未收錄**：產業新尖兵、微型創業鳳凰貸款等（無法從法規 API 驗證，需人工查證官網），本輪 MVP 判斷情境 A 不需要，暫不收錄。
3. **`career_tools.py` 尚未改讀新 schema**：Task 3 需將 `match_resources`／`calculate_benefit` 改為讀取本次的 `benefit.base`/`conditional_tiers`/`surcharges`/`concurrency_rules` 結構。
4. **`docs/IMPLEMENTATION_PLAN_20250731.md` 已重新改寫**（加入子代理平行執行策略、Wave 圖、子代理使用守則），將與本報告一併 commit。

---

## 相關檔案

- `agent/data/resources.json`（新增）
- `agent/data/constants.json`（新增）
- `output/laws_extracted.json`（暫存，已 gitignore）
- `output/run_local_extract.py`、`output/get_article.py`（一次性工具腳本，已 gitignore）
