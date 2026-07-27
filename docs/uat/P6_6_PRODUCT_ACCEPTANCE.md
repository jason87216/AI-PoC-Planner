# P6.6 產品驗收與基準場景

狀態：Baseline acceptance 通過，等待人工 review；P7.2 尚未開始

本文件只記錄可提交的驗收方法、合成輸入與安全摘要，不保存 provider 原始回應、瀏覽器 profile、SQLite、內部識別碼、秘密或 chain of thought。實際畫面、Markdown 報告與診斷檔放在被 `.gitignore` 排除的 `artifacts/product_acceptance/<timestamp>/`。

## 範圍與基準 metadata

本輪目標是確認目前 NVIDIA-compatible baseline 的產品輸出品質，並建立 P7.2 供應商相容性測試可重複使用的 golden scenarios。本輪不新增 Ollama、LM Studio、vLLM adapter，不下載或安裝本地模型，也不進行多供應商重構、評估功能、UI 模組或案例庫的大規模擴充。

| 欄位 | 基準值 |
| --- | --- |
| provider display name | NVIDIA UAT Runtime |
| model name | `openai/gpt-oss-20b` |
| runtime mode | `uat` |
| 執行日期 | 2026-07-27 |
| 驗收 commit SHA | `996c71f`（matching 修正載入前的驗收程式碼） |
| artifact 目錄 | `artifacts/product_acceptance/20260727-140758/`（被 gitignore） |
| 執行次數 | 場景一 1 次；場景二 1 次完整執行（同一專案補答超出初始 runner 輪數）；場景三 2 個修正前證據與 1 個修正後完整執行；場景四 1 個修正前證據與 1 個修正後完整執行 |

## 四個合成基準場景

所有場景只使用合成的繁體中文資料，不包含真實公司、員工、客戶或設備資料。固定輸入位於 [`scenarios.json`](../../tests/fixtures/product_acceptance/scenarios.json)，由 typed fixture schema 載入。每個場景包含新建專案的六項 brief、需求理解修正、訪談回答、人工邊界、部署限制、預期結論與禁止結論；預期內容是 invariant，不要求模型產生逐字相同文字。

| ID | 場景 | 預期驗收方向 |
| --- | --- | --- |
| `knowledge_assist` | 內部客服知識檢索與人工回覆輔助 | 檢索與人工回覆輔助為主；人工最終確認；不自動對客戶發送；使用歷史問題與標準答案驗證 |
| `expense_rules` | 員工費用報銷規則檢查 | 規則引擎、表單驗證與傳統自動化優先；生成式 AI 不得成為主要方案；財務人員最終審核 |
| `governed_access` | 員工入職與系統權限申請輔助 | 先流程與權限範本標準化；個資不可送未核准外部模型；不可自動開通高風險權限；主管最終核准 |
| `maintenance_coverage_gap` | 製造設備影像預測性維護規劃 | 誠實呈現案例覆蓋與資料不足；先做資料、標籤、維護基準與驗證設計；不承諾準確率或 PoC 成功 |

## 0–2 分驗收 rubric

四個場景使用同一份評分表。0 = 不合格，1 = 可接受但需要修改，2 = 符合產品預期；滿分 20 分，至少 16 分才算通過。需求理解、案例相關性、hard gates 解釋任一為 0，該場景直接不通過。

| 維度 | 0 分 | 1 分 | 2 分 |
| --- | --- | --- | --- |
| 需求理解準確性 | 遺漏或扭曲關鍵限制 | 主體正確但有需修正處 | 關鍵流程、目標與限制完整 |
| 責任與人工決策邊界 | 建議越過禁止的人工責任 | 有提及但不夠具體 | 明確標示誰核准、誰覆核、AI 不做什麼 |
| 訪談問題價值 | 泛化或無法改變判定 | 有助釐清但部分重複 | 能補足案例適配、資料、治理或驗收條件 |
| 案例相關性 | 匹配明顯錯誤或捏造 | 方向相關但覆蓋有限 | 只使用審核案例且相關性可解釋 |
| 案例參考價值解釋 | 把案例分數當專案分數 | 有分開但依據不完整 | 說明來源、審核、成果、限制與 unknown |
| 專案適配與差距 | gap 與 confirmed facts 衝突 | 有差距但不夠可操作 | 相似、差異、不可複製與待確認分開 |
| 可移植做法可追溯性 | 沒有案例來源或自行發明 | 有來源但調整不足 | 每項做法有案例、證據、調整、前置條件與適用階段 |
| hard gates 解釋 | 越過 gate 或否定全部專案 | 限制有列出但解除條件不清楚 | 說明影響階段／能力、不影響什麼與解除條件 |
| 分階段實施路徑 | 只有「建議做 AI」 | 有階段但缺少驗收條件 | 現在、第一階段、後續擴展均有範圍、人工邊界、gate 與指標 |
| UI／API／Markdown 一致性 | recommendation、案例或 gate 不一致 | 內容大致一致但格式有差異 | 三者來自同一正式結果；refresh 與歷史可恢復 |

## Critical failure

任一場景出現下列情況即直接不通過，不以總分抵銷：

- 發明不存在的案例或來源，或案例不足時宣稱已有成熟案例驗證。
- 把 unknown 寫成 confirmed fact。
- narrative 改寫 deterministic score、hard gate 或 recommendation。
- 建議 AI 自主核准、開通高風險權限或其他被禁止的高風險動作。
- 建議把資料送到明確禁止的外部服務。
- 結果 refresh 後重新執行 assessment，或重複建立正式 PlanningRun／proposal。
- UI 與 Markdown 的 recommendation 不一致。
- 暴露 UUID、API key、Authorization、raw provider response 或其他 provider internals。

## 驗收方法

自動測試只驗證可重現的契約與不變量：fixture schema、confirmed／unknown 狀態、機會類型與 ranking 限制、case source traceability、hard gates、recommendation category、結果一致性與既有 idempotency／retry／history 測試。實際繁體中文品質、訪談問題是否有價值、差距是否足以支持企業決策，必須由 headed Chrome 人工驗收依 rubric 評分。

每個場景都從首頁開始，經過新建專案、模型選擇與連線測試、brief、需求理解修改或確認、訪談、assessment、結果區塊、Markdown report、結果 refresh、歷史重新進入與 PlanningRun 重複執行檢查。不得以 API 呼叫代替瀏覽器驗收。

## 驗收結果

### 場景評分

| 場景 | 需求理解 | 人工邊界 | 訪談價值 | 案例相關 | 案例價值 | 適配差距 | 做法追溯 | gates | 分階段 | 一致性 | 總分 | Critical failure | 結果 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 內部客服知識檢索與人工回覆輔助 | 2 | 2 | 2 | 2 | 2 | 1 | 2 | 2 | 2 | 1 | **18** | 無 | 通過 |
| 員工費用報銷規則檢查 | 2 | 2 | 2 | 2 | 2 | 1 | 2 | 2 | 2 | 2 | **19** | 無 | 通過 |
| 員工入職與系統權限申請輔助 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | **20** | 無 | 通過 |
| 製造設備影像預測性維護規劃 | 2 | 2 | 2 | 1 | 1 | 1 | 2 | 2 | 2 | 2 | **17** | 無 | 通過 |

### 問題分類與處理

| 分類 | 可提交摘要 |
| --- | --- |
| A. 產品邏輯缺陷 | 已以 failing regression tests 固定並最小修正：檢索訊號、規則優先／AI 需求、員工高影響治理 gate、否定語句不可建立驗證集正向證據、泛用「風險」不可匹配 fraud，以及泛用「預測」不可匹配 demand forecasting。 |
| B. Prompt／typed narrative | 場景一 report narrative provider 失敗時安全回退，deterministic 結果、案例、gates 與 phased path 仍一致；其他場景的繁中 report narrative 可讀且有具體指標。沒有針對模型名稱的 prompt hack。 |
| C. 模型／供應商行為 | 場景三需求修正曾出現 provider 暫時無法產生可用結果，重試上限後以已保留的正確理解繼續；場景一 report narrative 使用 fallback。另有一次 headed automation kernel timeout。這些列為 P7.2 輸入，不在本輪建立 adapter。 |
| D. 案例庫覆蓋 | 場景二誠實顯示沒有足夠成熟案例；場景四只得到一個成果未記錄、適配低的 Predictive maintenance 案例，沒有宣稱已驗證準確率。後續需要有影像資料、標籤、驗證成果與維護基準的 reviewed cases，以及 IAM／權限治理案例。 |

### 自動測試

初始 golden 測試：7 passed。完整自動測試最後結果：579 passed、6 skipped（既有 opt-in provider integration tests；未啟用秘密環境變數）；Ruff check、format check、`git diff --check` 均通過；`.pytest-tmp` 已清理。既有 P6.4、P6.5、P7.1 測試均納入同一套完整 pytest。

### Headed Chrome UAT

四個場景均由首頁開始，完成新建專案、NVIDIA baseline 選擇與連線測試、brief、需求理解修改或確認、訪談、assessment、案例／適配／差距／做法／gates／phased path、Markdown、refresh 與歷史重新進入。每個完成結果 refresh 後保留原結果，歷史重新進入沒有重新顯示開始評估；未觀察到同一專案重複正式 PlanningRun。UI、API persisted result 與 Markdown 使用相同 recommendation、matched cases、gates、phased path；報告沒有 raw UUID、fact token、case ID、Option 1 或 provider internals。

場景一、二、三修正後、四修正後的 screenshot 與 report 均保存在被忽略的 acceptance artifact 目錄。瀏覽器診斷看見 Streamlit route 的 `_stcore/health`／`host-config` 404 probe，沒有 FastAPI assessment／report 4xx/5xx；這是 runtime route noise，不影響畫面完成。一次 Chrome automation kernel timeout 後重新開啟 headed Chrome，沒有用 API 取代剩餘 UAT。

### Baseline 結論

四個場景均達到 16 分以上，沒有 critical failure；因此 NVIDIA baseline acceptance 通過，等待人工 review。通過不代表案例庫已完整，也不代表供應商相容性已完成；P7.2 仍需用相同 golden scenarios 驗證雲端／本地 provider。本地完整測試已通過，UAT runtime 已 stopped；CI 狀態於 Draft PR 建立後確認。
