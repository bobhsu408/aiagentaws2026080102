# 職涯導航家 — 經實測的資料源清單

> 最後更新：2026-07-29
> 所有結果均為本 session 實際 curl / Python 測試，非紙上推測

---

## 一、全國法規資料庫 API ✅ 可用

### 基本資訊

| 項目 | 內容 |
|------|------|
| 提供者 | 法務部全國法規資料庫 |
| 認證 | **無需任何金鑰或認證** |
| 回傳格式 | ZIP 壓縮檔（內含 JSON + schema.csv + manifest.csv） |
| 編碼 | UTF-8 with BOM |
| 資料更新日 | 2026/7/17（實測取得） |
| 限制 | 無已知 rate limit；檔案較大需注意下載時間 |

### 端點

| 端點 URL | 內容 | 大小 | ZIP 內檔名 |
|---|---|---|---|
| `https://law.moj.gov.tw/api/Ch/Law/JSON` | 所有法律 + 憲法 | ~6 MB | `ChLaw.json` |
| `https://law.moj.gov.tw/api/Ch/Order/JSON` | 所有法規命令（辦法/準則/細則） | ~25 MB | `ChOrder.json` |

### JSON 結構

```json
{
  "UpdateDate": "2026/7/17 上午 12:00:00",
  "Laws": [
    {
      "LawLevel": "法律",
      "LawName": "就業保險法",
      "LawURL": "https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=N0050021",
      "LawCategory": "行政＞勞動部＞勞動保險目",
      "LawModifiedDate": "20220112",
      "LawEffectiveDate": "",
      "LawEffectiveNote": "",
      "LawAbandonNote": "",
      "LawHasEngVersion": "Y",
      "EngLawName": "Employment Insurance Act",
      "LawAttachements": [],
      "LawHistories": "1.中華民國九十一年...",
      "LawForeword": "",
      "LawArticles": [
        {
          "ArticleType": "C",
          "ArticleNo": "",
          "ArticleContent": "   第 一 章 總則"
        },
        {
          "ArticleType": "A",
          "ArticleNo": "第 16 條",
          "ArticleContent": "失業給付按申請人離職辦理本保險退保之當月起前六個月平均月投保薪資百分之六十按月發給，最長發給六個月。但申請人離職辦理本保險退保時已年滿四十五歲或領有社政主管機關核發之身心障礙證明者，最長發給九個月。..."
        }
      ]
    }
  ]
}
```

### 欄位說明（來自 schema.csv）

| 欄位名 | 說明 | 備註 |
|--------|------|------|
| `LawLevel` | 法規位階 | "法律" / "憲法"（Law端點）或 "命令"（Order端點） |
| `LawName` | 法規名稱 | 可用於篩選目標法規 |
| `LawURL` | 法規網址 | 可直接引用給使用者 |
| `LawCategory` | 法規類別 | 如 "行政＞勞動部＞勞動保險目" |
| `LawModifiedDate` | 法規異動日期 | 格式 YYYYMMDD |
| `LawArticles` | 法條陣列 | 見下方 |
| `ArticleType` | 條文型態 | "A" = 正式條文, "C" = 章節標題 |
| `ArticleNo` | 條號 | 如 "第 16 條", "第 19-1 條" |
| `ArticleContent` | 條文內容 | 全文，含款項分段 |

### 統計

| 端點 | 筆數 | LawLevel 分布 |
|------|------|---|
| Ch/Law/JSON | 1,345 | 法律 1,336 + 憲法 9 |
| Ch/Order/JSON | 10,440 | 全部為命令 |

### 使用範例（Python）

```python
import zipfile, json, io, urllib.request

url = "https://law.moj.gov.tw/api/Ch/Law/JSON"
data = urllib.request.urlopen(url).read()
z = zipfile.ZipFile(io.BytesIO(data))
laws = json.loads(z.read("ChLaw.json").decode("utf-8-sig"))["Laws"]

# 篩選就業保險法
ei = [l for l in laws if l["LawName"] == "就業保險法"][0]
for art in ei["LawArticles"]:
    if art["ArticleNo"].strip() == "第 16 條":
        print(art["ArticleContent"])
```

### 本專案相關法規清單（已確認存在）

**法律端點（Ch/Law/JSON）**：
- 就業保險法（55 條，修正 20220112）
- 就業服務法（92 條，修正 20250120）
- 職業訓練法（64 條，修正 20150701）
- 中高齡者及高齡者就業促進法（54 條，修正 20240731）
- 身心障礙者權益保障法（130 條，修正 20250801）

**命令端點（Ch/Order/JSON）**：
- 就業促進津貼實施辦法（40 條，修正 20250901）
- 就業保險促進就業實施辦法（79 條，修正 20250717）
- 失業中高齡者及高齡者就業促進辦法（57 條，修正 20250428）
- 就業保險失業者創業協助辦法（33 條，修正 20260610）
- 身心障礙者職務再設計實施方式及補助準則（19 條，修正 20160525）
- 育嬰留職停薪實施辦法（9 條，修正 20251121）
- 失業被保險人及其眷屬全民健康保險保險費補助辦法（6 條，修正 20121112）
- 就業保險延長失業給付實施辦法（7 條，修正 20100910）

### 從條文萃取到的關鍵金額（實測驗證）

| 法規 | 條號 | 金額/公式 |
|------|------|-----------|
| 就業保險法 §16 | 第 16 條 | 平均月投保薪資 × 60%，最長 6 月（45歲↑或身障→9月） |
| 就業保險法 §18 | 第 18 條 | 提早就業獎助 = 尚未請領失業給付金額 × 50%，一次發給 |
| 就業保險法 §19-1 | 第 19-1 條 | 每一受扶養眷屬加給 10%，上限 20% |
| 就業保險法 §19-2 | 第 19-2 條 | 育嬰留停津貼 = 平均月投保薪資 × 60%，每子女最長 6 月 |
| 就業促進津貼辦法 §8 | 第 8 條 | 求職交通補助每次 500 元（特殊 1,250），每年 4 次 |
| 就業促進津貼辦法 §12 | 第 12 條 | 臨時工作津貼 = 時薪最低工資，月合計不超月最低工資，最長 6 月 |
| 就業促進津貼辦法 §20 | 第 20 條 | 職訓生活津貼 = 最低工資 × 60%，最長 6 月（身障→1年） |
| 就業保險促進就業辦法 §28 | 第 28 條 | 異地就業交通補助 1,000/2,000/3,000 元（依距離），最長 12 月 |
| 就業保險促進就業辦法 §31 | 第 31 條 | 搬遷補助金核實最高 30,000 元 |
| 就業保險促進就業辦法 §34 | 第 34 條 | 租屋補助 = 租金 60%，月上限 5,000 元，最長 12 月 |
| 失業中高齡就業辦法 §41 | 第 41 條 | 僱用獎助：高齡全時 15,000/月、中高齡全時 13,000/月（發給雇主） |
| 就業保險失業者創業辦法 §7 | 第 7 條 | 創業貸款最高 200 萬元（或 50 萬） |
| 就業保險失業者創業辦法 §11 | 第 11 條 | 利率：郵政2年定儲+0.575%，前3年全額補貼 |

---

## 二、政府資料開放平臺（data.gov.tw）❌ 需 API Key

### 測試結果

```
POST https://data.gov.tw/api/v2/rest/dataset
→ 回應：{"success":false,"error":{"error_type":"ER0001:API Key錯誤","message":"API Key錯誤: HTTP 標頭沒設定 Authorization Key"}}
```

- v2 API 需申請 Authorization Key
- v1 API 已下線（404）
- 搜尋頁面是 Nuxt.js 前端渲染，無公開搜尋 API 可用
- 結論：**比賽時間壓力下不建議走申請流程**

### 替代方案

data.gov.tw 上的資料集可以透過瀏覽器手動下載 CSV/JSON，但無法程式自動取得。若需要特定資料集，建議手動下載後放入第 2 層。

---

## 三、台灣就業通（job.taiwanjobs.gov.tw）❌ 無公開 API

### 測試結果

```
GET https://job.taiwanjobs.gov.tw/Internet/index/opendata/JobList.json → 404
GET https://www.taiwanjobs.gov.tw/opendata → 404
```

- 網站存在但無公開 API 文件
- 頁面使用 Big5 編碼、.aspx 動態頁
- 搜尋結果暗示就業服務站有 JSON 端點（STATION_ID 等欄位出現在某處），但找不到穩定公開端點

### 替代方案

- Exa MCP 即時搜尋補充職缺/課程資訊
- 或手動從網站整理重點課程放入第 2 層

---

## 四、勞動力發展署開放資料（opendata.wda.gov.tw）❌ 連線逾時

### 測試結果

```
GET https://opendata.wda.gov.tw/api/course → 連線逾時（20秒無回應）
```

- 域名可能已停用或限制外部存取
- 無法確認是否有可用端點

---

## 五、iCAP 職能發展應用平台（icap.wda.gov.tw）⚠️ 有資料但無 API

### 觀察

- 網站有職能導向課程清單（1,337 項）
- 表格在前端渲染，無已知 JSON API
- 可手動查詢但無法自動取得

---

## 六、Exa AI MCP ✅ 已整合

### 基本資訊

| 項目 | 內容 |
|------|------|
| 端點 | `https://mcp.exa.ai/mcp` |
| 認證 | 無需認證 |
| 協定 | Streamable HTTP MCP |
| 整合方式 | `mcp_client/client.py` → Strands MCPClient |

### 能力

- 網路搜尋（query → 相關網頁摘要）
- 網頁爬取（URL → 文本內容）
- 程式碼搜尋

### 限制

- 無 timeout 設定（目前程式碼）
- 無 fallback（Exa 掛了 Agent 會卡住）
- 回傳品質不穩定（可能回傳不相關結果）
- 非官方權威來源，不適合作為金額/資格的唯一依據

---

## 七、總結比較表

| 資料源 | 可用性 | 認證 | 格式 | 更新 | 本專案用途 |
|--------|--------|------|------|------|-----------|
| 全國法規資料庫 API | ✅ 穩定 | 免 | ZIP→JSON | 每週 | 資格/金額/期限（核心） |
| data.gov.tw API | ❌ 需key | 申請制 | JSON | 不定 | 放棄 |
| 台灣就業通 | ❌ 無API | — | — | — | 手動整理或 Exa 搜 |
| opendata.wda.gov.tw | ❌ 逾時 | 不明 | — | — | 放棄 |
| iCAP | ⚠️ 網頁only | — | HTML | 不定 | 手動參考 |
| Exa AI MCP | ✅ 已整合 | 免 | MCP | 即時 | 補充動態資訊 |
