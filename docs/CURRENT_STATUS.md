# 現況速覽（維護入口）

> 最後更新：2026-08-02 12:00
> 用途：新 session 接手維護時的第一份文件。只寫「現在是什麼狀態」，
> 歷史脈絡看 `docs/HANDOFF.md`，踩坑細節看 `docs/reports/TASK_7_REPORT.md`。

---

## 一、一句話現況

**Demo 已可用**，評審打開一個網址就能操作完整流程（問卷 → 補助試算 → 行動計畫時間軸）。

**Demo 網址**：https://d133na3jc4epsg.cloudfront.net

---

## 二、線上資源清單（改東西前先看這裡）

| 資源 | 值 |
|---|---|
| AWS 帳號 / 區域 | `881768789243` / `us-west-2` |
| CloudFront Distribution ID | `E390L9I6IKXN7S` |
| Demo 網址 | https://d133na3jc4epsg.cloudfront.net |
| 前端 S3 bucket | `careernav-frontend-881768789243`（**完全私有**，僅 CloudFront OAC 可讀） |
| Chat Proxy Lambda | `careernav-chat-proxy`（Function URL 為 `AWS_IAM`，不對外直接暴露） |
| AgentCore Runtime ARN | `arn:aws:bedrock-agentcore:us-west-2:881768789243:runtime/careernav_careernav-Su5fjSE2LM` |
| CloudFormation Stack | `CareerNavStack` |

**警告**：每次 `cdk deploy` 若 CloudFront 被重建，**Demo 網址會變**。
部署後一律以 stack output `DemoUrl` 為準，不要沿用文件裡的舊網址。

---

## 三、目前架構

```
瀏覽器（GET /chat?q=&session_id=）
   ▼
CloudFront（單一公開網址，Origin Access Control 代做 SigV4 簽名）
   ├── /*     → S3（前端靜態檔，私有 bucket）
   └── /chat  → Lambda Function URL（AuthType = AWS_IAM）
                  ▼
            Lambda careernav-chat-proxy（解析 SSE，組出 reply + roadmap）
                  ▼
            AgentCore Runtime（Strands Agent + 六步驟 Career Tools + Exa MCP）
```

**為什麼要有 CloudFront**（這是本專案最重要的一個限制，別拆掉）：
比賽沙盒帳號的 guardrail **封鎖匿名（`AuthType: NONE`）的 Lambda Function URL**
（實測回 403），但**允許 SigV4 簽名呼叫**（實測回 200）。所以必須有一層能代簽的
東西，CloudFront + OAC 就是那一層。詳見 `docs/reports/TASK_7_REPORT.md` 第二節。

---

## 四、Task 進度

| Task | 狀態 |
|---|---|
| Task 1～6 | 已完成，各有報告於 `docs/reports/` |
| **Task 7：Lambda Proxy + 前端接入** | **已完成**（十個步驟全部），報告：`docs/reports/TASK_7_REPORT.md` |
| 語音輸入（額外項目，非計畫內） | 由另一 session 完成，報告：`docs/reports/VOICE_INPUT_REPORT.md` |
| Task 8～9 | 尚未開始 |

Git：本地與 `origin/main` 已同步，最新 commit `724c523`。
遠端 repo：`https://github.com/bobhsu408/aiagentaws2026080102`

---

## 五、前端功能現況（`frontend/index.html`，單一檔案）

| 功能 | 說明 |
|---|---|
| 快速評估問卷 | 8 題選擇題，**每題都有「其他（自行輸入）」**。點選即進下一題 |
| 一鍵示範情境 | 首頁按鈕，載入 58 歲資遣情境，demo 最快路徑 |
| 兩段式送出 | 第 1 段資格+試算、第 2 段時間軸+文件清單（見下方「為什麼拆兩段」） |
| Markdown 渲染 | 支援標題／粗體／清單／分隔線／連結，先 escape HTML 再套規則 |
| 逐區塊淡入 | 取代逐字打字機，總時長上限 1.2 秒 |
| 等待進度 | 分步驟推進（解析背景→比對方案→試算金額），降低等待感 |
| 規劃圖 | 收到 roadmap 時先出通知卡，點擊後切到專屬全寬時間軸畫面 |
| 敘述不足補問 | 使用者講太少時，回覆後提供「開啟快速評估選單」提示卡，每對話僅一次 |
| 語音輸入 | 麥克風按鈕（另一 session 實作，見 `VOICE_INPUT_REPORT.md`） |

### 為什麼拆兩段（別合回一段）

單一請求跑完六步驟實測達 **59 秒**，而 CloudFront 對 origin 的回應上限是
**60 秒**（超過需申請配額，審核來不及）。拆開後第 1 段約 19 秒、第 2 段約 8 秒，
且時間軸的觸發不再依賴模型自行決定要不要呼叫工具。

### 為什麼用 GET 不用 POST（別改回 POST）

CloudFront OAC 對 **POST** 要求呼叫端自行計算 body 的 SHA256 並帶
`x-amz-content-sha256`（Lambda 不接受 unsigned payload）。改用 GET 後沒有 body，
CloudFront 可獨立完成整個簽名，**瀏覽器端零簽名邏輯**。
`lambda/proxy.py` 仍保留 POST 分支，要改回時可用。

---

## 六、日常維護指令

**注意**：workspace 所在磁碟是 `noexec`，npm / cdk / agentcore CLI **必須**在
`~/careernav`（rsync 副本）執行。

```bash
# 同步 workspace → ~/careernav
rsync -av --delete \
  --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
  --exclude='cdk.out' --exclude='agentcore/.cli' \
  "/media/data/共用文件/專案開發/aws/hoyilive/" "$HOME/careernav/"

# 載入 AWS credentials
cd ~/careernav && set -a && source .env && set +a

# 只改前端 → 上傳 + 清快取（最常用，不需重新部署基礎設施）
aws s3 cp ~/careernav/frontend/index.html \
  s3://careernav-frontend-881768789243/index.html \
  --content-type "text/html; charset=utf-8" --region us-west-2
aws cloudfront create-invalidation --distribution-id E390L9I6IKXN7S --paths "/*"

# 改基礎設施或 Lambda → 部署
cd ~/careernav/infra && npx cdk deploy --require-approval never

# 改 Agent 程式碼（app/careernav/）→ 重新部署 Runtime
cd ~/careernav && agentcore deploy   # 詳見 docs/DEPLOY_NOTES.md
```

### 前端測試

jsdom 行為測試在 `/tmp/frontend_test/`（**`/tmp` 是暫存，新機器不存在，需重建**）：

```bash
mkdir -p /tmp/frontend_test && cd /tmp/frontend_test && npm init -y && npm install jsdom
```

| 腳本 | 覆蓋範圍 | 斷言數 |
|---|---|---|
| `wizard_test.js` | 狀態機、問卷流程、Markdown 渲染、通知卡與規劃圖切換、錯誤與重試 | 26 |
| `extra_test.js` | 八題都有「其他」、敘述完整度判斷 | 13 |
| `ui_test.js` | 等待步驟顯示、敘述不足提示卡 | 7 |
| `voice_test.js` | 語音輸入（另一 session 建立） | — |

改完前端請全部重跑。視覺驗證可用：

```bash
google-chrome --headless=new --disable-gpu --no-sandbox \
  --force-prefers-reduced-motion \
  --screenshot=/tmp/shot.png --window-size=1280,900 \
  "file:///media/data/共用文件/專案開發/aws/hoyilive/frontend/index.html"
```

> 加 `--force-prefers-reduced-motion` 是因為 headless 的 virtual time 不推進
> CSS 動畫，不加會拍到半透明的中間狀態，誤以為畫面壞了。

---

## 七、已知限制與雷區

1. **單次請求上限 60 秒**：自由對話若一句話要求走完六步驟仍可能逾時。
   前端兩段式流程已規避，但使用者自行輸入時無法保證。

2. **同一 session 不可併發**：`app/careernav/main.py` 以 session_id 快取 Agent
   實例，同 session 併發會共用對話歷史導致回應為空。前端已加 in-flight 鎖、
   CloudFront 已設 `connectionAttempts: 1` 關閉重試。不同 session 併發沒問題。

3. **模型偶爾聲稱已呼叫工具卻沒呼叫**：第 2 段指令必須明確寫「請務必實際呼叫
   工具（系統需要結構化資料才能繪圖）」，前端另有一次自動補要機制。別把這段
   指令改得太客氣。

4. **CloudFront OAC 需要兩條 Lambda 權限**：`lambda:InvokeFunctionUrl`（CDK 自動加）
   + `lambda:InvokeFunction`（**CDK 不會自動加，已在 stack.ts 手動補**）。
   缺第二條時 CloudFront 一律回 403。別移除 `AllowCloudFrontInvokeFunction`。

5. **`x-amz-content-sha256` 不可放進 OriginRequestPolicy**：會在部署階段直接失敗。

6. **LINE 功能在此帳號做不了**：LINE 平台只發普通 POST、不會做 SigV4 簽名，
   而匿名 Function URL 被擋、OAC 對 POST 又要求 body 雜湊。唯一可行路徑是
   加一層 Lambda@Edge（us-east-1，權限未驗證）。
   原始碼已備份於 `backup/line_webhook.py`，詳見 `TASK_7_REPORT.md` 第七節。

7. **`/chat` 無使用者層級認證**：任何人拿到網址都能呼叫並消耗 Bedrock 額度。
   這是「評審直接開網址就能用」的必要取捨。

8. **前端連結對照表是靜態副本**：`RESOURCE_LINKS` / `COURSE_LINKS` 是
   `resources.json` / `courses.json` 的精簡版，資料更新時要手動同步。

9. **`.kiro` 不可加入 `.gitignore`**：比賽硬性規定，`.gitignore` 已加註說明。
   若日後新增 `.kiro/settings/mcp.json`，注意金鑰不得硬編碼。

10. **多人同時部署會互相覆蓋**：本日曾發生 CloudFront 架構被另一個部署移除。
    動 `cdk deploy` 前先確認沒有其他人正在部署（stack 狀態需為 `*_COMPLETE`）。

---

## 八、時程風險（比賽當下）

依報到通知：**AWS 開發環境僅開放至 8/2（日）14:00**，但競賽進行到 19:00、
評審簡報在 14:00 之後。

→ **14:00 之後現場 Live Demo 可能連不上 AWS**（前端、Lambda、AgentCore
Runtime 全在沙盒帳號內）。這也是繳交清單同時要求「Live Demo 網址連結」與
「**Live Demo 錄製影片連結**」的原因。**務必在 14:00 前完成影片錄製。**

---

## 九、Demo 操作動線（已實測）

1. 開啟 https://d133na3jc4epsg.cloudfront.net
2. 點「**一鍵示範情境**」（最快）或「開始評估」走 8 題問卷
3. 約 19 秒 → 出現補助方案與試算
   （每月 25,410 元、9 個月、總計 228,690 元，附法規條號）
4. 約 8 秒 → 出現「✓ 已為您生成專屬轉職規劃圖」通知卡
5. 點「**點擊瀏覽規劃圖**」→ 全寬橫式時間軸
   （4 階段、1 決策點、法規與課程連結可點擊）
6. 點「返回對話」可繼續追問

---

## 十、相關文件

| 文件 | 內容 |
|---|---|
| `docs/reports/TASK_7_REPORT.md` | 本次踩坑全記錄、技術決策理由、LINE 無法運作的原因鏈 |
| `docs/HANDOFF.md` | Task 1～6 的歷史脈絡與決策紀錄（較長，非必讀） |
| `docs/IMPLEMENTATION_PLAN_20250731.md` | 唯一正式計畫 |
| `docs/DEPLOY_NOTES.md` | AgentCore 部署步驟與同步指令 |
| `docs/aws技術文件.txt` | 工作坊環境限制與規範（S3 不可公開、Bedrock < 1 RPS 等） |
| `docs/reports/VOICE_INPUT_REPORT.md` | 語音輸入實作（另一 session） |
