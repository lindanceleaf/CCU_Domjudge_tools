# DOMjudge 9.0.0 帳號匯入工具設計

## 目標

將 CSV 名單轉換成 DOMjudge 9.0.0 可匯入的 groups、teams 與 accounts 資料，並提供一個入口依正確順序完成三項匯入。

## 輸入規則

- `DATA_DIR` 指向名單目錄，預設為目前目錄。
- 每個 CSV 第一列為標題，前兩欄依序為姓名與學號；其餘欄位忽略。
- 檔名比對 `TA.csv` 時不分大小寫。
- 空白列、少於兩欄的列及空學號列略過。
- 同一類資料出現重複學號時只保留第一次，要建立的項目，並顯示警告。

## 模組與責任

### `create_groups.py`

- 掃描 `DATA_DIR` 中所有 CSV。
- 排除 `TA.csv`。
- 每個其餘 CSV 以不含副檔名的檔名建立一個 group；`id` 與 `name` 都使用該檔名。
- 產生 `groups.json`，再以 multipart 欄位 `json` 上傳至 `/api/v4/users/groups`。
- 沒有學生 CSV 時產生空陣列並略過 API 上傳。

### `create_teams.py`

- 只讀取 `TA.csv` 以外的 CSV。
- 每位學生建立一個 team，`id` 使用學號、`name` 使用姓名、`group_ids` 包含 CSV 檔名對應的 group。
- 不替 TA 建立 team。
- 產生 `teams.json`，再以 multipart 欄位 `json` 上傳至 `/api/v4/users/teams`。

### `create_accounts.py`

- 一般學生建立 `type: team` 的帳號，`id`、`username` 及初始 `password` 使用學號，`team_id` 使用相同學號以綁定已建立的 team。
- `TA.csv` 中每位人員建立 `type: admin` 的帳號。依 DOMjudge 9.0.0 的 account JSON/YAML 匯入邏輯，admin 會自動取得 `team` role，DOMjudge 會在隱藏的 `Jury` category 建立或重用對應 team，並將 admin 綁定至該 team，因此 TA 可以提交程式。
- TA 不設定 `team_id`；若設定，DOMjudge 9.0.0 仍會優先使用上述自動建立的 Jury team。學生帳號才以 `team_id` 綁定 `create_teams.py` 已建立的 team。
- 產生 `accounts.yaml`，再以 multipart 欄位 `yaml` 上傳至 `/api/v4/users/accounts`。

### `setup_domjudge.py`

- 載入並驗證 `DOMJUDGE_URL`、`API_USER`、`API_PASS` 與 `DATA_DIR`。
- 共用同一個已設定 Basic Authentication 的 HTTP session。
- 直接呼叫三個模組公開的 Python 函式，不以子程序執行腳本。
- 嚴格依 groups、teams、accounts 的順序執行；任一步驟失敗即停止，回傳非零結束碼。
- 各小功能仍可個別執行自己的 `.py`。

## 錯誤處理

- 缺少環境變數、找不到 CSV 或讀取失敗時，在送出 API 請求前停止。
- API 連線失敗、逾時或非成功 HTTP 狀態要顯示端點、狀態碼與 DOMjudge 回應摘要。
- 不使用 `/api/users/...` 自動降級端點；本工具明確支援 DOMjudge 9.0.0 的 `/api/v4`。
- 輸出檔只有在內容成功產生後才寫入。

## Repository 安全與檔案

- `.env`、真實名單 CSV、產生的 `groups.json`、`teams.json`、`accounts.yaml` 不納入 Git。
- Repository 提供不含個資的範例 CSV 與 `.env.example`。
- Python 相依套件固定記錄於 dependency file；README 說明 DOMjudge 9.0.0、設定與四種執行方式。

## 測試與驗收

- 單元測試涵蓋：排除 TA group、排除 TA team、學生 team 分組、學生帳號明確設定 `team_id`、TA admin 交由 DOMjudge 自動建立並綁定 Jury team、重複學號與空資料列。
- HTTP 測試以假 session 驗證 DOMjudge 9.0.0 端點、multipart 欄位及 groups → teams → accounts 呼叫順序，不接觸正式伺服器。
- 全部測試通過後，才使用目前 `.env` 對指定 DOMjudge 進行唯讀連線檢查；實際匯入由使用者明確執行，避免測試資料寫入正式系統。
