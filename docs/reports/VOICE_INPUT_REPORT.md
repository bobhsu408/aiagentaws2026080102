# 語音輸入實作報告 — Amazon Transcribe Streaming

日期：2026-08-02
程式碼進版：`55889e7`（與 Task 7 前端改動一併提交，該 commit 訊息未提及語音）

## 目標

對話框加入語音輸入。要求：功能若來不及做，至少要有麥克風圖示與點擊後的「聆聽中」動畫。
實作結果是兩者都有 — 真實辨識可用，且任何失敗都會退回示範動畫，不會讓畫面開天窗。

## 架構

```
瀏覽器  ──① GET /chat?action=voice_url──▶  CloudFront ──OAC──▶ Lambda (careernav-chat-proxy)
        ◀─── presigned wss URL（5 分鐘）───                    │ SigV4QueryAuth 代簽
                                                              ▼
        ──② wss 直連（不經 CloudFront）──▶  transcribestreaming.us-west-2.amazonaws.com:8443
        ◀─── partial / final 逐字稿 ────
```

設計決策：

- **不用瀏覽器內建 Web Speech API**。那是把音訊送到 Google 的服務，不在本專案的 AWS
  架構內；且非 Google Chrome 的 Chromium / Brave / Electron 沒有 Google API key，
  一定回 `network` 錯誤（實測遇過）。改用 Amazon Transcribe 才符合比賽的 AWS 架構要求。
- **簽章由 Lambda 代做**。presigned URL 的權限等同簽章者，所以權限只需給 Lambda 執行角色，
  瀏覽器不持有任何 AWS 憑證。URL 有效期 300 秒。
- **WebSocket 直連 Transcribe，不經 CloudFront**。WebSocket 沒有 CORS 限制，不必為它
  新增 CloudFront behavior。
- **沿用 `/chat` 這條 behavior**，用 `action=voice_url` 參數區分，不新增 behavior。

## 檔案改動

| 檔案 | 內容 |
|------|------|
| `lambda/proxy.py` | 新增 `GET /chat?action=voice_url` 分支與 `_voice_url_response()`，用 `botocore.auth.SigV4QueryAuth` 代簽 wss URL，回傳 `url` / `language_code` / `sample_rate` / `expires_in` |
| `infra/lib/stack.ts` | `agentRole` 新增 `transcribe:StartStreamTranscriptionWebSocket`（streaming 無資源層級 ARN，只能用 `*`） |
| `frontend/index.html` | 麥克風按鈕 + 聆聽動畫 CSS、語音狀態列 HTML、Transcribe streaming 的完整 JS 實作 |

### 前端實作要點

- **音訊管線**：`getUserMedia` → `AudioContext({ sampleRate: 16000 })`（讓瀏覽器代為
  重取樣，省掉自寫 resampler）→ `ScriptProcessor(4096)` 取 Float32 → 轉 16-bit 小端 PCM
  → AWS event stream 編碼（自寫 CRC32 查表）→ WebSocket。
  `ScriptProcessor` 必須連到 `destination` 才會被驅動，中間插一個 `gain = 0` 的節點避免回音。
- **收尾**：送一個空的 `AudioEvent`（104 bytes，只有 3 個 header）告知音訊結束，
  Transcribe 回最後一段 final 後關閉連線。
- **圖示**：6 個 `<rect>` 疊出的像素風麥克風 SVG，`fill="currentColor"`，
  所以按鈕 hover 反白時圖示自動變黑，與既有復古視覺語彙一致。

### 動畫保底機制

`VOICE_MIN_LISTEN_MS = 2600`。所有結束訊息一律經 `scheduleListeningFinish()` 排隊，
等聆聽動畫播滿 2.6 秒才顯示。原因：辨識引擎失敗常在 0.3 秒內就回來，若立刻收動畫，
使用者只會看到動畫閃一下就跳錯誤字，等於沒有動畫。

- 引擎在保底時間內結束（成功或失敗）→ 動畫繼續播到時間到，訊息之後才出現。
- 使用者主動結束（再點麥克風、送出訊息、重新開始）→ 立即停止，不套保底時長，操作手感不拖。
- 失敗一次後記 `voiceServiceBroken`，之後點麥克風直接走示範動畫，按鈕標成虛線框
  （`.demo-only`），不再每次白等一輪失敗。

降級路徑（都會播完整動畫再提示，並請使用者改用文字輸入）：

| 情況 | 提示 |
|------|------|
| 非 HTTPS / 無 `getUserMedia` | 此環境無法取用麥克風 |
| 麥克風權限被拒 | 請在瀏覽器網址列允許麥克風 |
| 拿不到簽章 URL | 無法取得語音服務授權，已切換示範模式 |
| WebSocket 連線失敗 / 伺服器例外 | 語音服務連線失敗，已切換示範模式 |

### 無障礙

`aria-label` / `aria-pressed`（聆聽中切 true）、狀態列 `role="status" aria-live="polite"`、
鍵盤 `focus-visible` 虛線外框、`prefers-reduced-motion` 關閉所有裝飾性動畫。

## 驗證結果

| 項目 | 方法 | 結果 |
|------|------|------|
| 沙盒帳號可用 Transcribe Streaming | Polly 合成 zh-TW 語音 → presigned wss → 送 PCM | 通過。partial 逐字出現，final = 「我今年58歲，被公司資遣，想知道可以申請哪些補助。」繁體正確 |
| Lambda `action=voice_url` | 本機以真實憑證呼叫 `proxy.handler` → 用回傳的 URL 實際連線辨識 | 通過。回 200，辨識出「我想申請職業訓練生活津貼。」 |
| 前端邏輯 | jsdom，43 項斷言 | 全數通過 |
| 動畫不被錯誤打斷 | jsdom 檢查 0.6 秒 / 2.0 秒 / 2.6 秒三個時點 | 通過。前兩點仍 `.listening`，2.6 秒後才顯示提示 |
| CDK | `tsc --noEmit`、`cdk synth` | 通過，模板含新權限 |
| 真機麥克風 | — | **未驗**，需部署後在 CloudFront https 網址實測 |

`language-code=zh-TW` 在 streaming 可用，輸出為繁體中文，不需要另做簡繁轉換。

## 待辦

1. `cd infra && cdk deploy` — 套用 IAM 權限與 Lambda 新程式碼（缺權限時 `action=voice_url` 會回 500，前端會自動退回示範模式，不會壞掉）。
2. 上傳 `frontend/index.html` 到 `careernav-frontend-881768789243` 並做 CloudFront invalidation。
3. 在 CloudFront https 網址用 Chrome 實測講話回填。
4. 決定 `VOICE_AUTO_SEND`：目前 `false`（辨識完讓使用者確認再送出）。若要台上全程免手打，改 `true`。

## 已知限制

- `ScriptProcessorNode` 已被標為棄用（建議改 `AudioWorklet`），但在現行瀏覽器仍可用，
  且不需要額外的 Blob URL / worklet 檔案。時間充裕時可換。
- presigned URL 5 分鐘到期，超過後需重新點麥克風（每次點擊都會重新取一條）。
- Transcribe streaming 對長時間無聲的連線會主動關閉；前端另設 `VOICE_MAX_LISTEN_MS = 30000`
  作為最長聆聽時間，避免忘記關麥克風。
