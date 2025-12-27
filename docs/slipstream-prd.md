# Slipstream - 產品需求文件 (PRD)

## 專案概述

**專案名稱：** Slipstream

**專案類型：** CLI Tool（命令列工具）→ 未來延伸為 MCP Server

**開發時間：** 8 小時（週末專案）

**技術棧：** Python, Google Drive API, Google Vision API, Anthropic Claude Haiku 4.5, Google Sheets
API

### 產品願景

打造一個命令列工具來自動化收據處理流程。使用者手動上傳收據圖片到 Google Drive
指定資料夾後，工具會自動讀取、辨識、結構化並匯出至 Google Sheets，提升費用報銷和記帳的效率。未來可延伸為
MCP Server，提供更靈活的整合方式。

### 工作流程

```
使用者手動上傳收據 → Google Drive 資料夾
                ↓
         CLI Tool 讀取圖片
                ↓
         Google Vision OCR
                ↓
      Claude Haiku 結構化
                ↓
      匯出到 Google Sheets
```

---

## 核心目標

1. **自動化資料擷取**：從 Google Drive 資料夾讀取收據圖片，透過 OCR 技術自動辨識文字資訊
2. **智能資料結構化**：運用 LLM 將非結構化文字轉換為標準格式
3. **無縫資料整合**：直接匯出至 Google Sheets，方便後續處理和分析
4. **簡單易用**：透過命令列介面快速執行，支援批次處理

---

## 使用者故事

### 主要使用者角色

- **個人使用者**：需要記錄日常消費的個人
- **小型企業員工**：需要整理費用報銷單據的員工
- **自由工作者**：需要追蹤業務開支的 freelancer

### 核心使用者故事

**故事 1：基本收據處理**
> 身為一個需要報銷費用的員工，我會先將收據照片上傳到 Google Drive 的指定資料夾，然後執行 CLI
> 工具，系統自動提取商家名稱、日期、金額、項目等資訊，並整理到 Google Sheets 中，這樣我就不用手動輸入這些資料。

**故事 2：批次處理**
> 身為一個月底需要整理帳務的使用者，我會將一個月的收據都上傳到 Google Drive，然後執行一次 CLI
> 指令，系統能夠批次處理並匯總到同一個試算表中。

**故事 3：定期執行**
> 身為一個定期需要處理收據的使用者，我希望能設定 cron job 或排程任務，讓工具自動定期檢查 Google Drive
> 資料夾並處理新上傳的收據。

---

## 功能需求

### Phase 1：CLI 工具核心功能（MVP - 8小時內完成）

#### 1. Google Drive 整合模組

**優先級：P0**

- 整合 Google Drive API
- 從指定資料夾讀取圖片檔案
- 支援常見圖片格式（JPG, PNG, PDF）
- 追蹤已處理檔案（避免重複處理）

**驗收標準：**

- 能成功連接 Google Drive
- 能列出指定資料夾中的所有圖片
- 能下載圖片到本地暫存
- 能標記已處理的檔案

#### 2. OCR 資料擷取模組

**優先級：P0**

- 整合 Google Vision API
- 支援常見收據格式（直式/橫式）
- 輸入：收據圖片檔案（從 Drive 下載）
- 輸出：Raw text data

**驗收標準：**

- 能正確辨識清晰收據上的中英文文字
- 辨識準確率 > 85%
- 單張收據處理時間 < 5 秒

#### 3. LLM 資料結構化模組

**優先級：P0**

- 使用 Anthropic Claude Haiku 4.5
- 從 raw text 中提取結構化資訊
- 輸出標準化 JSON 格式

**必要欄位：**

```json
{
  "merchant_name": "商家名稱",
  "date": "YYYY-MM-DD",
  "total_amount": "總金額（數字）",
  "currency": "幣別",
  "items": [
    {
      "description": "項目描述",
      "quantity": "數量",
      "unit_price": "單價",
      "amount": "小計"
    }
  ],
  "tax": "稅額",
  "payment_method": "付款方式（如果有）",
  "invoice_number": "發票號碼（如果有）"
}
```

**驗收標準：**

- 能從 raw text 中正確提取 80% 以上的關鍵資訊
- 能處理格式不完整的收據
- 能識別並標記不確定的資料

#### 4. Google Sheets 匯出模組

**優先級：P0**

- 整合 Google Sheets API
- 支援建立新試算表或寫入現有試算表
- 自動格式化欄位（日期、金額等）

**試算表結構：**
| 檔案名稱 | 日期 | 商家 | 項目 | 數量 | 單價 | 金額 | 總計 | 幣別 | 發票號碼 | 付款方式 |
處理時間 |

**驗收標準：**

- 能成功寫入資料到 Google Sheets
- 資料格式正確且易於閱讀
- 支援錯誤重試機制

#### 5. CLI 介面實作

**優先級：P0**

**主要指令：**

```bash
# 處理指定 Google Drive 資料夾中的所有收據
# 支援 Folder ID 或完整的分享連結
slipstream process --folder <FOLDER_ID_OR_URL> --sheet <SHEET_ID_OR_URL>

# 範例：使用 ID
slipstream process --folder 1AbCdEfGhIjKlMnOpQrStUvWxYz --sheet 1XyZwVuTsRqPoNmLkJiHgFeDcBa

# 範例：使用分享連結
slipstream process \
  --folder "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz" \
  --sheet "https://docs.google.com/spreadsheets/d/1XyZwVuTsRqPoNmLkJiHgFeDcBa/edit"

# 處理單一檔案
slipstream process-file --file <FILE_ID_OR_URL> --sheet <SHEET_ID_OR_URL>

# 列出 Drive 資料夾中的檔案
slipstream list --folder <FOLDER_ID_OR_URL>

# 顯示處理歷史
slipstream history

# 設定 credentials
slipstream config --google-creds <PATH> --anthropic-key <KEY>
```

**URL 解析功能：**

工具會自動識別並解析以下格式的 URL：

| 類型             | URL 格式                                             | 解析結果         |
|----------------|----------------------------------------------------|--------------|
| Drive 資料夾      | `https://drive.google.com/drive/folders/{ID}`      | 提取 Folder ID |
| Drive 資料夾 (u/) | `https://drive.google.com/drive/u/0/folders/{ID}`  | 提取 Folder ID |
| Drive 檔案       | `https://drive.google.com/file/d/{ID}/view`        | 提取 File ID   |
| Google Sheets  | `https://docs.google.com/spreadsheets/d/{ID}/edit` | 提取 Sheet ID  |

**進階選項：**

- `--dry-run`: 預覽而不實際執行
- `--verbose`: 顯示詳細日誌
- `--force`: 強制重新處理已處理的檔案
- `--output-json`: 將結構化資料輸出為 JSON 檔案

**驗收標準：**

- CLI 介面清晰易用
- 自動識別 ID 或 URL 輸入
- 支援各種 Google Drive/Sheets URL 格式
- URL 解析錯誤時提供清楚的錯誤訊息
- 錯誤訊息友善且有幫助
- 支援基本的 help 文檔
- 進度顯示清楚（批次處理時）

---

### Phase 2：延伸功能（8小時後的迭代）

#### 6. MCP Server 實作

**優先級：P1**

將 CLI 工具的核心功能包裝成 MCP Server，讓 Agent（如 Claude）能透過 tools 呼叫。

**可用工具（Tools）：**

1. `list_drive_receipts`
    - 輸入：Google Drive 資料夾 ID
    - 輸出：資料夾中的收據檔案列表

2. `process_receipt`
    - 輸入：Google Drive 檔案 ID
    - 輸出：結構化 JSON 資料

3. `export_to_sheets`
    - 輸入：結構化資料、試算表 ID
    - 輸出：寫入狀態

4. `process_folder`
    - 輸入：資料夾 ID、試算表 ID
    - 輸出：批次處理結果（組合工具）

**技術考量：**

- 使用 stdio transport（本地 MCP Server）
- 支援 SSE transport（遠端存取）
- 環境變數管理
- 錯誤處理和狀態回報

**驗收標準：**

- MCP Server 能正常啟動並響應請求
- 工具介面清晰且符合 MCP 規範
- Agent 能正確理解和使用所有 tools

#### 7. 進階功能

**優先級：P2**

- **增量處理**：只處理新上傳的檔案
- **錯誤通知**：處理失敗時發送通知（Email 或 Slack）
- **資料驗證**：在匯出前進行資料品質檢查
- **成本追蹤**：記錄 API 使用量和成本
- **報表生成**：產生處理統計和費用摘要

---

## 開發時程（8小時規劃）

### Hour 1-2：環境設定與 Google Drive 整合

- [x] 建立 Python 專案結構
- [x] 設定 Google Drive API credentials（透過 gcloud auth application-default login 設定開發權限）
- [ ] **實作 URL 解析器（支援 Drive/Sheets URL）**
- [ ] 實作 Drive 資料夾讀取功能
- [ ] 實作檔案下載功能
- [ ] 建立測試收據樣本（上傳到 Drive）

### Hour 3-4：OCR 與 LLM 模組開發

- [ ] 整合 Google Vision API
- [ ] 撰寫 OCR 功能測試
- [ ] 設計 LLM prompt template
- [ ] 整合 Anthropic API
- [ ] 實作資料驗證和清理

### Hour 5-6：Google Sheets 整合與 CLI 介面

- [ ] 設定 Google Sheets API
- [ ] 實作寫入功能
- [ ] 格式化試算表
- [ ] 實作基本 CLI 指令（click/typer）
- [ ] 整合 URL 解析器到 CLI 參數處理
- [ ] 新增進度顯示（rich）
- [ ] 測試 ID 和 URL 兩種輸入方式

### Hour 7：檔案追蹤與批次處理

- [ ] 實作 SQLite 資料庫（追蹤已處理檔案）
- [ ] 實作批次處理邏輯
- [ ] 錯誤處理和重試機制
- [ ] 日誌記錄

### Hour 8：整合測試與文檔

- [ ] 端對端測試
- [ ] 效能優化
- [ ] 撰寫 README 和使用說明
- [ ] 準備 requirements.txt 和安裝腳本

---

## 資料模型

### Receipt Data Schema

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class ReceiptItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: float


class Receipt(BaseModel):
    merchant_name: str
    date: date
    total_amount: float
    currency: str = "TWD"
    items: List[ReceiptItem]
    tax: Optional[float] = None
    payment_method: Optional[str] = None
    invoice_number: Optional[str] = None
    confidence_score: float = Field(ge=0, le=1)
    raw_text: str
    processed_at: datetime
```

---

## 評估與品質保證

本專案採用系統化的評估方法，確保 LLM 結構化品質和 Agent-MCP 互動的正確性。

詳細的評估設計、測試案例和評估指標請參閱：
**[評估設計文件 (Evaluation Design)](./evaluation-design.md)**

評估重點包含：

- **LLM 結構化模組評估**：欄位準確率、結構完整度、語意一致性
- **Agent-MCP Tool 互動評估**：30 個測試案例，涵蓋單一工具、組合工具、錯誤處理、多輪對話等場景
- **端對端系統評估**：整體成功率、效能指標、錯誤分析

---

## 成功指標

### MVP 階段（CLI Tool）

1. **功能完整度**：核心功能（Drive 整合、OCR、LLM、Export、CLI）全部正常運作
2. **LLM 結構化準確度**：
    - LLM 結構化準確率 > 80%
    - 關鍵欄位（總金額、商家、日期）準確率 > 90%
    - 結構完整度 > 85%
    - 端對端成功率 > 85%
3. **CLI 使用體驗**：
    - 指令清晰易懂
    - 錯誤訊息友善有幫助
    - 批次處理進度顯示清楚
    - Help 文檔完整
4. **效能**：
    - LLM 處理時間 (P95) < 6 秒
    - 批次處理 10 張收據 < 2 分鐘
5. **測試覆蓋**：
    - 完成 30 張測試收據的評估
    - 單元測試覆蓋率 > 80%
    - CLI 指令測試覆蓋率 > 90%

### 延伸功能階段（MCP Server）

1. **MCP 整合完成度**：MCP Server 正常運作，所有 tools 可用
2. **Agent-MCP 互動品質**：
    - Tool 選擇準確率 > 90%
    - 參數完整性 > 95%
    - 錯誤處理得分 > 2.5/3.0
    - Agent 互動測試通過率 > 85%
3. **可用性**：能透過 Claude Code 或其他 MCP client 順利使用

---

## 風險與應對策略

### 技術風險

**風險 1：Google Drive API 配額限制**

- **影響**：無法讀取大量收據檔案
- **機率**：中
- **應對**：
    - 實作 rate limiting
    - 分批處理大量檔案
    - 建立 API 用量監控
    - 提供本地快取機制

**風險 2：檔案追蹤機制失效**

- **影響**：重複處理相同檔案，浪費 API 配額
- **機率**：低
- **應對**：
    - 使用可靠的 SQLite 資料庫
    - 實作事務處理確保一致性
    - 提供 `--force` 選項手動控制
    - 定期備份追蹤資料庫

**風險 3：不同收據格式差異大**

- **影響**：LLM 提取準確度波動
- **機率**：高
- **應對**：
    - 設計強健的 prompt engineering
    - 提供多個 prompt 範本
    - 實作信心分數機制
    - 建立 few-shot examples 庫

**風險 4：Google API 認證複雜度**

- **影響**：使用者設定困難，開發時間增加
- **機率**：中
- **應對**：
    - 使用 service account（簡化認證流程）
    - 準備詳細的設定文件和截圖
    - 提供 `slipstream config` 互動式設定
    - 檢查常見錯誤並提供友善提示

**風險 5：批次處理時部分檔案失敗**

- **影響**：使用者需要手動識別失敗檔案
- **機率**：中高
- **應對**：
    - 詳細的錯誤日誌記錄
    - 產生失敗報告（列出失敗檔案和原因）
    - 提供重試失敗檔案的指令
    - Continue-on-error 模式（不因單一失敗中斷）

### 時程風險

**風險 5：8 小時內無法完成所有功能**

- **影響**：延遲交付或功能刪減
- **機率**：中高
- **應對**：
    - 嚴格遵循 MVP 優先級
    - 預先準備程式碼範本和範例
    - 延伸功能列為 Phase 2

---

## 部署與維護

### MVP 部署方式

- 本地執行 MCP Server
- 透過 `stdio` transport 與 Claude Code 連接

### 未來部署方式（Remote MCP）

1. **容器化**：使用 Docker 打包應用
2. **雲端平台**：部署到 Railway / Render / Fly.io
3. **監控**：設定基本的 logging 和錯誤追蹤
4. **文件**：提供 API 文件和使用範例

### 維護計畫

- 定期更新 API credentials
- 監控 API 用量和成本
- 收集使用者回饋並優化 prompt
- 持續改善辨識準確率

---

## 附錄

### A. 環境變數配置

```bash
# .env.example
GOOGLE_CLOUD_VISION_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
GOOGLE_SHEETS_CREDENTIALS_PATH=./credentials.json
DEFAULT_SPREADSHEET_ID=your_spreadsheet_id

# Optional for Remote MCP
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000
AUTH_TOKEN=your_secure_token
```

### C. 參考資源

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Google Cloud Vision API](https://cloud.google.com/vision/docs)
- [Anthropic API Reference](https://docs.anthropic.com/)
- [Google Sheets API](https://developers.google.com/sheets/api)

---

## 版本歷史

| 版本  | 日期         | 變更內容               | 作者    |
|-----|------------|--------------------|-------|
| 1.0 | 2025-12-26 | 初始版本               | Claud |
| 1.1 | 2025-12-27 | 更新專案名稱為 Slipstream | Claud |

---

**最後更新：** 2025-12-27
