# 我用 Python 清理 1,676 部 YouTube 喜歡影片：從 OAuth、API 配額到安全批次的完整實戰

## 五個候選標題

1. 我用 Python 清理 1,676 部 YouTube 喜歡影片：OAuth 與配額踩坑實錄
2. YouTube 沒有「批次取消喜歡」？我做了一個安全優先的 Python CLI
3. 從 Dry-run 到 Human-in-the-loop：一個真正會修改帳號的自動化工具該怎麼設計
4. Cursor 寫了程式、Codex 完成落地：AI 協作開發 YouTube 清理工具實錄
5. 只留下最近九部：YouTube Data API v3 的批次清理工程

## 開場：一個看似簡單、其實很危險的需求

我的 YouTube「喜歡的影片」累積了很多年。某天我想把它變成一個真正有用的短清單：只留下最近按讚的九部，其餘全部取消喜歡。

手動處理 1,676 部影片幾乎不可能。直覺上，這只是「抓清單、跳過九筆、逐筆取消」；但只要程式排序錯一次，就可能把最想保留的內容刪掉。它還牽涉 Google OAuth、YouTube API 配額、失效影片、Windows 中文編碼，以及真正會改變雲端帳號的破壞性操作。

這個專案最重要的成果，不是寫出一個迴圈，而是建立一條可以信任的自動化工作流。

## 背景：為什麼這個問題不好解

YouTube 網頁沒有提供大量取消喜歡的正式介面。瀏覽器自動化雖然可行，卻容易受 UI 改版、延遲與登入狀態影響；因此我選擇官方 YouTube Data API v3。

API 本身也有三個限制。第一，需要 Desktop OAuth，因為「喜歡」屬於私人帳號資料。第二，讀取播放清單與修改 rating 使用不同的 API 操作。第三，每次修改都消耗配額，不能假設一次可以處理上千部。

因此架構從一開始就採取四層保護：dry-run、明確確認、批次上限、JSON 稽核報告。

## Debug 過程

### 第一關：程式存在，檔案卻消失了

Cursor Cloud Agent 最初把工具寫在另一個 repository 的 PR 裡，之後又依需求將變更移除，改成一個沒有真正交付成功的 ZIP artifact。PR 最後合併時淨變更為零。

解法不是重寫，而是從 Git 歷史找回第一個 commit。Git 的價值在此非常具體：即使最終分支已經刪掉檔案，blob 仍可從歷史 commit 復原。我把四個原始檔案取回，建立獨立 repository，再推送到 GitHub。

### 第二關：OAuth JSON 不等於 API 已可用

取得 `client_secret.json` 後，OAuth 登入成功，`token.json` 也建立了；第一次 API 呼叫卻回傳 403：專案尚未啟用 YouTube Data API v3。

這讓我重新區分兩個概念：OAuth Client 決定「誰可以要求使用者授權」，API enablement 決定「這個 Google Cloud 專案能不能呼叫服務」。兩者缺一不可。

啟用 API 後，工具成功讀出 Liked videos 的特殊播放清單 ID `LL`，並分頁取得 1,676 筆資料。

### 第三關：Windows CP950 遇到全球內容

清單抓到了，程式卻在輸出第一批標題時出現 `UnicodeEncodeError`。原因不是 YouTube 資料錯誤，而是 Windows 傳統終端使用 CP950，無法表示某些簡體字與 emoji。

短期用 `PYTHONUTF8=1` 解決；長期則在程式啟動時重新設定 stdout/stderr 為 UTF-8 並使用 replace fallback。這是常被忽略的 production 細節：資料處理成功，不代表可觀測性也成功。

### 第四關：真實世界的清單並不乾淨

第一個正式批次設定最多 180 部。實際結果為 102 部成功、3 部失敗：兩部回傳 404，一部回傳 403。404 通常代表影片已刪除或資源不可見；403 可能是特殊權限狀態或配額訊號。

程式沒有重頭再跑，也沒有丟失成功紀錄，而是停止後把結果寫入報告。這比「追求 100% 一次完成」更符合安全工程。

## Solution：把危險操作拆成可審核狀態機

完整流程如下：

1. OAuth 登入並快取 token。
2. 取得目前使用者的 Liked videos playlist。
3. 依 YouTube 回傳順序分頁讀取所有項目。
4. 將前 N 筆放入 keep，其餘放入 planned unlike。
5. 預設只列印並寫入報告。
6. 只有 `--execute` 加人工確認才開始修改。
7. `--max-unlike` 限制單次影響範圍。
8. 遇到速率、配額或權限訊號時停止，保留已完成進度。

它有效的原因，是把「決策」與「執行」分開。Dry-run 產生一個可核對的決策面；execute 才是副作用面。AI 可以協助建立工具、找出錯誤與操作介面，但最後的帳號變更仍由人確認，這正是 Human-in-the-loop。

## 我學到什麼

架構上，我學到 destructive automation 必須內建可逆思維，即使 API 操作本身不可逆，也能靠預覽、限量與報告降低爆炸半徑。

工具上，我更清楚 Git 歷史不只是協作紀錄，也是災難復原機制；Google OAuth 與 API enablement 則是兩個相互獨立的控制面。

Workflow 上，Cursor 適合快速生成初版，Codex 則接手本機整合、憑證安全、實際驗證、GitHub 發布與瀏覽器操作。AI 協作真正的價值，不是讓人離開流程，而是讓人把注意力放在授權與風險判斷。

## 可以避免哪些坑

- 不要把 `client_secret.json`、`token.json` 或含私人觀看資料的報告提交到 Git。
- 不要第一次執行就加 `--execute --yes`。
- 不要把 OAuth 成功誤認為 API 已啟用。
- 不要假設每部影片仍可被 rating API 操作。
- 不要忽略 Windows 終端編碼。
- 不要一次吃滿每日配額；為 retry 與人工驗證保留空間。
- 不要把 AI 產生的程式直接連到 production 帳號，先測試純函式與 dry-run。

## 結論

這個專案最大的收穫是：可靠的自動化，不是做得最快，而是每一步都能被看見、限制、停止與追溯。

## SEO

- **SEO Title:** 用 Python 批次清理 YouTube 喜歡影片：OAuth、API 配額與 Dry-run 實戰
- **Meta Description:** 從 1,676 部 YouTube 喜歡影片中只保留最近九部，完整解析 Python、YouTube Data API v3、Google OAuth、配額控制、Windows Unicode 與 Human-in-the-loop 安全設計。
- **URL Slug:** `python-youtube-liked-videos-cleanup-oauth-api`

## Tags

Python, YouTube API, OAuth, GitHub, Codex
