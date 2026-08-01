# ⚠️ 此目錄已停用（DEPRECATED）

自 Task 3 起，六步驟 Career Tools 與資料檔已統一至 **`app/careernav/`**
（AgentCore Runtime 實際打包部署的目錄），作為唯一真實來源（single source of truth）。

## 為什麼

原本 `agent/` 與 `app/careernav/` 兩套程式碼並存，但 `agentcore deploy`
只打包 `app/careernav/`（見 `agentcore/agentcore.json` 的 `codeLocation`）。
若在 `agent/` 開發、卻部署 `app/careernav/`，會造成 Runtime 吃不到新程式碼與資料。

## 現在的位置

| 內容 | 新位置 |
|------|--------|
| 六步驟工具 | `app/careernav/tools/career_tools.py`（@tool 封裝）+ `logic.py`（純邏輯） |
| 支援模組 | `app/careernav/tools/{data_loader,formula,profile}.py` |
| 補助資料 | `app/careernav/data/resources.json` |
| 全局常數 | `app/careernav/data/constants.json` |
| 課程資料 | `app/careernav/data/courses.json` |
| 單元測試 | `app/careernav/tests/test_career_tools.py` |

本目錄保留僅供歷史參考，請勿在此新增或修改程式碼。
