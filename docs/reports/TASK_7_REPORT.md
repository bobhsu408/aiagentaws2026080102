# Task 7 完成報告 — Lambda Proxy + 前端接入（精簡版）

**日期**：2026-08-02
**Demo 網址**：https://d133na3jc4epsg.cloudfront.net
**Commit**：`55889e7`

---

## 一、最終架構（與原計畫的差異）

原計畫第一節設想的是「瀏覽器 → Lambda Function URL（AuthType.NONE）」，
**實際不可行**，改為：

```
瀏覽器（GET /chat?q=&session_id=）
   ▼
CloudFront（單一公開網址，Origin Access Control 代做 SigV4 簽名）
   ├── /*     → S3（前端靜態檔，bucket 完全私有）
   └── /chat  → Lambda Function URL（AuthType = AWS_IAM）
                  ▼
            AgentCore Runtime（careernav_careernav-Su5fjSE2LM）
```

改動理由見下節「二、關鍵技術發現」第 1 點。

---

## 二、關鍵技術發現（本次踩坑紀錄，下個 session 請先看這段）

### 1. 沙盒帳號封鎖「匿名」Lambda Function URL，但允許「簽名」呼叫

實測同一個 Function URL：

| AuthType | 呼叫方式 | 結果 |
|---|---|---|
| `NONE` | 匿名 curl | **403 Forbidden**（`AccessDeniedException`） |
| `AWS_IAM` | SigV4 簽名 | **200 OK**，回覆正常 |
| — | `aws lambda invoke`（走 AWS API） | **200 OK** |

設定本身沒問題（`AuthType` 確實是 `NONE`、resource policy 確實有
`Principal: *` + `lambda:InvokeFunctionUrl`），是**帳號層級的 guardrail**
在攔。無權查 `organizations:ListPoliciesForTarget` 佐證，但行為特徵符合
Organization 層級的 SCP／RCP。

→ 結論：此帳號要對外開放 HTTP，必須有一層「能代做 SigV4 簽名」的東西。

### 2. CloudFront OAC 呼叫 Lambda Function URL 需要「兩條」權限

CDK 的 `FunctionUrlOrigin.withOriginAccessControl()` 只會自動加
`lambda:InvokeFunctionUrl`，**缺少 `lambda:InvokeFunction`**，
缺這條時 CloudFront 一律回 403。

AWS 文件 [Restrict access to an AWS Lambda function URL origin](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-lambda.html)
的「Grant CloudFront permission」段落明確列出兩道 `add-permission` 指令。

已在 `infra/lib/stack.ts` 以 `proxyLambda.addPermission()` 補上，勿移除。

### 3. `x-amz-content-sha256` 不可放進 OriginRequestPolicy

嘗試把它加入白名單會在部署階段直接失敗：

```
The parameter Headers contains x-amz-content-sha256 that is not allowed
```

它是 CloudFront OAC 自己管理的簽名 header，viewer 送來後 CloudFront 會
自行讀取使用，不需（也不能）透過 OriginRequestPolicy 轉發。

### 4. 改用 GET 可完全繞開 POST 的 body 雜湊要求

OAC 對 **POST/PUT** 要求呼叫端自行計算 body 的 SHA256 並帶
`x-amz-content-sha256`（Lambda 不接受 unsigned payload）。
改成 `GET /chat?q=...&session_id=...` 後沒有 body，CloudFront 可獨立完成
整個簽名，**瀏覽器端零簽名邏輯**。

代價：訊息長度受 URL 限制（約 8KB，對聊天足夠）、訊息會出現在 CloudFront
存取日誌（demo 環境不涉及真實個資，可接受）。

`lambda/proxy.py` 同時保留 POST 分支，方便日後改回。

### 5. CloudFront origin 回應逾時上限 60 秒

預設只有 30 秒，且**逾時後 CloudFront 會對 GET 重試**，重試打進同一個
session 會拿到空回應。已設 `readTimeout: 60s` + `connectionAttempts: 1`。

超過 60 秒需申請「origin response timeout」配額提升（審核需時，來不及）。
→ 因此把六步驟拆成兩段請求（見下節第 6 點）。

### 6. 同一 session 併發會讓 Agent 對話狀態壞掉

`app/careernav/main.py` 以 session_id 為 key 快取 Agent 實例。
同一 session 同時兩個請求會共用同一個 Agent 與其對話歷史，實測回應變空
（`Empty reply parsed from AgentCore stream, raw length=188`）。

不同 session_id 併發沒問題（各自獨立 Agent 實例）。
前端已加 in-flight 鎖；CloudFront 端已關閉重試。

另註：工作坊規範要求 Bedrock 請求低於 1 RPS，本來就不該高併發。

### 7. 模型偶爾「聲稱已呼叫工具」但實際沒呼叫

第 2 段請求若只寫「請接著執行 generate_roadmap」，模型會回
「我剛才已經執行完成」而**實際沒呼叫工具**，導致前端拿不到 roadmap
資料、畫不出時間軸。

解法：指令明確寫「請務必實際呼叫工具（系統需要工具回傳的結構化資料才能
繪圖，只用文字描述無法繪圖）」，並在前端加一次自動補要。

---

## 三、前端實作要點

單檔 `frontend/index.html`，與原計畫的差異：

| 項目 | 計畫 | 實際 | 原因 |
|---|---|---|---|
| 回覆呈現 | 逐字打字機 25ms/字 | 逐 Markdown 區塊淡入，總時長上限 1.2 秒 | 回覆常達 1200+ 字，逐字要跑 30 秒以上，live demo 無法等 |
| 文字格式 | 純文字 | 加 Markdown 渲染 | Agent 回覆是 Markdown，純文字會把 `**`、`##` 原樣印出來 |
| 時間軸位置 | 直接嵌入對話串 | 先出「已生成規劃圖」通知卡 → 點擊進專屬全寬畫面 | 對話串塞大圖會擠壓版面；demo 動線也更清楚 |
| 資料收集 | 多輪對話追問 | 8 題選擇題問卷（可「其他」自填）+ 一鍵示範情境 | 多輪問答走到試算與時間軸太慢，demo 需要快速觸發 |

Markdown 渲染有做 HTML 轉義（先 `escapeHtml` 再套 Markdown 規則），
連結只允許 `http`/`https` scheme。

---

## 四、端到端測試結果

對正式 CloudFront 網址實測，情境 A（58 歲工廠作業員因自動化被資遣）：

| 階段 | HTTP | 耗時 | 回覆字數 | roadmap |
|---|---|---|---|---|
| 前端載入 `GET /` | 200 | — | 72,729 bytes | — |
| 第 1 段（資格 + 試算） | 200 | 18.9s | 359 | None（符合預期） |
| 第 2 段（時間軸 + 文件） | 200 | 8.2s | 159 | **有** |

第 2 段回傳的時間軸結構：4 個階段、1 個決策點、2 門 curated 課程。

金額驗算正確：
- 失業給付：36,300 × 60% = 21,780；眷屬加給 21,780 × 10% × 1 = 3,630
- 合計每月 25,410 元；因滿 45 歲延長為 9 個月；總計 228,690 元
- 法規條號引用正確（就業保險法第 11、16、19-1 條）

前端自動化測試：`jsdom` 26 項斷言全數通過（狀態機、問卷流程、
Markdown 渲染、通知卡與規劃圖畫面切換、錯誤與重試情境）。

---

## 五、安全性與合規

### 已處理

- **S3 不再公開**：`BlockPublicAccess.BLOCK_ALL`（四項全開，已用
  `get-public-access-block` 確認），僅 CloudFront OAC 可讀。
  舊的 S3 website 公開網址現已回 404。
  這是工作坊規範的硬要求：「DO NOT create S3 bucket without restriction」。
- **Lambda 不直接對外暴露**：Function URL 改 `AWS_IAM`，只接受
  CloudFront（以 distribution ARN 條件限定）的簽名呼叫。
- **憑證未進版控**：`.env` 已由 `.gitignore` 第 27 行排除；
  commit 前已掃描 `AKIA`/`ASIA`/`aws_secret_access_key`/`SessionToken` 樣式，無命中。

### 仍存在的風險

- **`/chat` 無使用者層級認證**：任何人拿到 CloudFront 網址都能呼叫，
  進而消耗 Bedrock 額度。這是「評審直接開網址就能用」的必要取捨。
  正式產品應加 Cognito 或 WAF rate limiting。
- **訊息內容進入 CloudFront 存取日誌**：因為改用 GET，query string 會被記錄。
  正式產品若處理真實個資，應改回 POST（並自行處理 body 雜湊）。

---

## 六、已知限制與未完成事項

1. **LINE webhook 在此帳號無法運作**（重要，見下節）
2. **單次請求上限 60 秒**：若使用者用一句話要求走完六步驟，實測可達 59 秒，
   逼近上限。前端的兩段式流程已規避，但自由對話仍可能觸發。
3. **時間軸課程掛載規則簡化**：目前把 curated 課程掛在含
   `training_living_allowance` 的節點，未依 `linked_resource_id` 精準對應。
4. **前端連結對照表為靜態打包**：`RESOURCE_LINKS` / `COURSE_LINKS` 是
   `resources.json` / `courses.json` 的精簡副本，資料更新時需手動同步。

---

## 七、給 LINE 功能開發者的提醒（避免重踩）

LINE webhook **不能用匿名 Lambda Function URL**，原因是一條鎖鏈：

1. LINE 平台推 webhook 只發普通 POST，不會做 AWS SigV4 簽名
2. 匿名 Function URL（`AuthType: NONE`）被帳號 guardrail 擋 → 403
3. 想用 CloudFront OAC 代簽？但 OAC 對 **POST** 要求呼叫端自行計算 body
   SHA256 並帶 `x-amz-content-sha256` —— LINE 不會做這件事
4. 我們的網頁能用是因為改成 **GET**（無 body 免雜湊）；LINE 沒這個選項

**唯一可行路徑**：加一層 **Lambda@Edge**（`origin-request` 階段可讀 body，
代算雜湊並補上 header）。需部署在 us-east-1，此帳號權限未驗證。

原始碼已保存於 **`backup/line_webhook.py`**（234 行，自 CDK asset 還原）。
該檔只從環境變數讀 LINE 憑證，無硬編碼。原本部署的 Lambda 環境變數裡
有 `LINE_CHANNEL_SECRET` / `LINE_CHANNEL_ACCESS_TOKEN`，若要還原需重新設定。

> 註：`careernav-line-webhook` Lambda 已因本次 CloudFront 部署被 CloudFormation
> 移除（不在本 stack 模板中）。移除前已備份原始碼。

---

## 八、時程風險（需團隊決策）

依報到通知，**AWS 開發環境僅開放至 8/2 (日) 14:00**，但競賽進行到 19:00、
評審簡報在 14:00 之後。

→ **14:00 之後的現場 Live Demo 可能無法連上 AWS**（前端、Lambda、
AgentCore Runtime 全在沙盒帳號內）。

這也解釋了為何繳交清單同時要求「Live Demo 網址連結」與
「**Live Demo 錄製影片連結**」。建議在 14:00 前務必完成影片錄製，
不要把評審時的呈現全押在即時連線上。

---

## 九、部署與更新指令

```bash
# 部署基礎設施
cd ~/careernav/infra && set -a && source ../.env && set +a
npx cdk deploy --require-approval never

# 更新前端（改完 index.html 後）
aws s3 cp ~/careernav/frontend/index.html \
  s3://careernav-frontend-881768789243/index.html \
  --content-type "text/html; charset=utf-8" --region us-west-2
aws cloudfront create-invalidation --distribution-id E390L9I6IKXN7S --paths "/*"
```

**注意**：每次 `cdk deploy` 若 CloudFront 被重建，**Demo 網址會變**。
部署後請以 stack output `DemoUrl` 為準。
