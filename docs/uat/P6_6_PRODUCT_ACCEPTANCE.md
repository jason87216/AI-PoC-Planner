# P6.6 產品驗收與基準場景

狀態：技術基準驗收通過；產品負責人的最終繁中語言／企業情境審核延後至 P8.1；P7.2 尚未開始。

本文件只保存可提交的驗收方法與安全摘要，不保存 provider 原始回應、瀏覽器 profile、SQLite、秘密、內部識別碼或 chain of thought。實際 screenshot、Markdown 與診斷檔位於被 `.gitignore` 排除的 `artifacts/product_acceptance/20260727-140758/`。

## Baseline metadata

| 欄位 | 基準值 |
| --- | --- |
| provider | NVIDIA UAT Runtime |
| model | `openai/gpt-oss-20b` |
| runtime | `uat` |
| 日期 | 2026-07-27 |
| deterministic 基準 commit | `e2f789c` |
| 最終流程執行 | 四個場景各一次完整 headed Chrome UAT |

## Golden scenarios

固定合成輸入位於 [`scenarios.json`](../../tests/fixtures/product_acceptance/scenarios.json)，並由 typed fixture schema 載入。預期內容是 invariant，不要求模型逐字產生相同文字。

| ID | 場景 | 核心預期 |
| --- | --- | --- |
| `knowledge_assist` | 內部客服知識檢索與人工回覆輔助 | 檢索＋人工確認，不自動對外發送 |
| `expense_rules` | 員工費用報銷規則檢查 | 規則引擎／表單驗證優先，不強迫使用生成式 AI |
| `governed_access` | 員工入職與系統權限申請輔助 | 主管最終核准，個資與高風險權限受 gate 限制 |
| `maintenance_coverage_gap` | 製造設備影像預測性維護規劃 | 資料、標籤與驗證設計優先，不承諾準確率 |

## Acceptance rubric

每個維度 0–2 分，滿分 20，至少 16 分通過。需求理解、案例相關性或 hard-gate 解釋任一為 0 時直接不通過。

維度：需求理解、人工決策邊界、訪談價值、案例相關性、案例參考價值、適配與差距、做法追溯、hard gates、分階段路徑、UI／API／Markdown 一致性。

Critical failure 包含：

- 發明案例、來源或「成熟案例驗證」；
- 把 unknown 改寫成 confirmed；
- narrative 改寫 deterministic recommendation、score 或 gate；
- 建議自主核准、高風險權限開通或禁止的外部資料處理；
- refresh／history re-entry 重做 assessment 或重複建立正式結果；
- UI 與 Markdown 使用不同正式結果；
- 暴露 UUID、API key、Authorization 或 raw provider response。

## Final scores

| 場景 | 分數 | 結果 | 扣分原因 |
| --- | ---: | --- | --- |
| 內部客服知識檢索與人工回覆輔助 | 18/20 | 通過 | reviewed-case 依賴／治理仍有 unknown；report narrative 使用 fallback |
| 員工費用報銷規則檢查 | 19/20 | 通過 | 沒有足夠 approved case，無法提供完整案例 fit／gap |
| 員工入職與系統權限申請輔助 | 20/20 | 通過 | 無 |
| 製造設備影像預測性維護規劃 | 17/20 | 通過 | 案例偏泛化、成果未記錄、缺少標籤／驗證集／維護基準 |

四個場景均無 critical failure。

## Formal categories and gates

| 場景 | recommendation category | deterministic gates |
| --- | --- | --- |
| 客服知識檢索 | `ai_hybrid` | HG-01、HG-05、HG-06；無 employment HG-03 |
| 費用報銷 | `rules_first` | HG-01、HG-05、HG-06；無 employment HG-03 |
| 權限申請 | `governed_assistive` | HG-01、HG-03、HG-05、HG-06 |
| 預測性維護 | `readiness_first` | HG-01、HG-05、HG-06 |

正式 category 由 confirmed facts、deterministic matching 與 gates 推導；provider option kind 不得覆寫正式結果。

## Provider narrative status

| 場景 | 產品流程 | provider narrative | fallback |
| --- | --- | --- | --- |
| 客服知識檢索 | 完整成功 | report narrative 未成功 | 是，僅 report narrative |
| 費用報銷 | 完整成功 | 成功 | 否 |
| 權限申請 | 完整成功 | 需求修正曾部分失敗；最終 report 成功 | 否 |
| 預測性維護 | 完整成功 | 成功 | 否 |

Fallback 不計為 provider 成功；正式 recommendation、案例、gates 與 phased path 始終以 deterministic persisted result 為準。

## Verification

- Golden expectation parameterized tests 經正式 application result composition 驗證 opportunity、category、gaps、phases、禁止結論、人工邊界、部署限制與 key conclusions。
- 完整結果：`601 passed, 6 skipped`；六個 skipped 為需要秘密或本機 endpoint 的既有 opt-in provider tests。
- Ruff check、format check、`git diff --check` 與 GitHub Actions 通過。
- Headed Chrome 從首頁完成新建、模型測試、brief、理解／修正、訪談、assessment、案例／gap／practice／gates／phased path、Markdown、refresh 與 history re-entry。
- 未觀察到重複正式 PlanningRun；UI、persisted API result 與 Markdown 使用同一正式結果。
- UAT runtime 已停止。

## Conclusion

P6.6 的技術與自動化 baseline acceptance 通過，並可作為 P7.2 雲端／本地 provider 的 golden baseline。這不代表案例庫完整，也不代表供應商相容性完成。

產品負責人未在最後版本上完成實機語言與企業情境審核，因此該項明確延後至 P8.1，不宣稱已通過，也不要求為此重開 P6 功能開發。
