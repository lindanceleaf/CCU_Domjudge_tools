# CCU DOMjudge Tools

[繁體中文](README.md) | [English](README.en.md)

從 CSV 名單建立 DOMjudge groups、teams 與帳號，並提供題目骨架產生與上傳工具。
目前以 DOMjudge 9.0.0 為目標版本。`examples/` 內皆為虛構資料，可安全複製使用。

## 安裝與設定

需要 Python 3.10 以上版本。在專案目錄執行：

```powershell
python -m pip install -e .
ccudj --help
```

接著將 `.env.example` 複製為 `.env`：

```dotenv
DOMJUDGE_URL=https://judge.example.edu
API_USER=admin
API_PASS=your-password
DATA_DIR=rosters/fall
```

CSV 第一列必須是 `name,id`，後面可以有 `email` 等額外欄位。除了 `TA.csv`
之外，每個 CSV 檔名都代表一個學生 group；`TA.csv` 用來建立 admin accounts。
真實名單、`.env`、產生的匯入檔與 zip 已由 `.gitignore` 排除。

## 名單匯入

| 指令 | 產生檔案 | 行為 |
| --- | --- | --- |
| `ccudj groups` | `groups.json` | 依非 TA 的 CSV 檔名建立 groups。 |
| `ccudj teams` | `teams.json` | 為非 TA 名單中的學生建立 teams。 |
| `ccudj accounts` | `accounts.yaml` | 建立學生 team accounts 與 TA admin accounts。 |
| `ccudj setup` | 上述三個檔案 | 依 groups → teams → accounts 順序全部匯入。 |

這些不是預覽指令：產生檢查檔後，若有資料就會向 `.env` 指定的 DOMjudge
送出 API 請求。`ccudj setup` 會先產生全部內容，確認 CSV 都能讀取後才開始
上傳；任一階段失敗即停止。

舊指令仍可直接執行：

```powershell
python create_groups.py
python create_teams.py
python create_accounts.py
python setup_domjudge.py
python upload_problem.py hello
```

### 只產生檔案、不上傳

以下函式不需要 API 帳密，也不會發出網路請求：

```python
from pathlib import Path
from domjudge_tools.roster.groups import generate_groups, save_groups
from domjudge_tools.roster.teams import generate_teams, save_teams
from domjudge_tools.roster.accounts import generate_accounts, save_accounts

data_dir = Path("rosters/fall")
save_groups(generate_groups(data_dir), data_dir / "groups.json")
save_teams(generate_teams(data_dir), data_dir / "teams.json")
save_accounts(generate_accounts(data_dir), data_dir / "accounts.yaml")
```

`teams.json` 格式：

```json
[
  {
    "id": "S100001",
    "group_ids": ["CAT"],
    "name": "Ada Example"
  }
]
```

`accounts.yaml` 格式：

```yaml
- id: S100001
  username: S100001
  password: S100001
  type: team
  name: Ada Example
  team_id: S100001
- id: T900001
  username: T900001
  password: T900001
  type: admin
  name: Taylor Sample
```

學生帳號綁定同 ID 的 team。TA admin 不指定 `team_id`；DOMjudge 9.0.0 會為
管理員帳號建立並綁定隱藏的 Jury team。

## 題目工具

建立題目骨架：

```powershell
ccudj problem new hello 2 512
ccudj problem new --name hello --timelimit 2 --memory 512
```

參數依序為名稱、時間限制（秒）、記憶體限制（MiB）；預設為 `1.0` 秒與
`256` MiB。舊指令 `python gen_problem.py ...` 仍可使用。

```text
hello/
├── problem.yaml
├── domjudge-problem.ini
├── data/
│   ├── sample/
│   └── secret/
└── submissions/
    └── accepted/
        └── AC.c
```

`problem.yaml` 儲存名稱、輸出比對模式與記憶體限制；DOMjudge 9.0.0 的時間
限制則寫入 `domjudge-problem.ini`：

```ini
name = hello
timelimit = 2.0
```

完成 `problem.html`、`problem.pdf` 或 `problem.txt` 其中一份非空題本、
`AC.c` 與至少一組同名 `.in`／`.ans` 後，可執行原有的
驗證、打包與上傳流程：

```powershell
ccudj problem upload hello
```

此指令也支援原有的 `--AC`、`--pdf`、`--save` 選項。
`--pdf` 是略過題本檢查的舊名稱，新名稱為 `--skip-statement-check`。

### 工具、題庫與課程資料分開存放

工具安裝後可使用題目資料夾的相對或絕對路徑。以下結構可分別管理工具、私人題庫與本機課程資料：

```text
workspace/
├── domjudge-tools/            # 本專案
├── problem-bank/
│   ├── problems/
│   │   └── new-problem/       # 題本、設定、data/、submissions/
│   ├── authoring/            # 測資產生與答案驗證程式
│   ├── records/              # 測資說明與上傳紀錄
│   └── dist/                 # 題目 ZIP
└── course-data/
    └── 115-1/
        ├── .env
        ├── rosters/
        └── generated/
```

可將設定放在課程資料夾，使用 `--env` 指定（可放在子指令前或後）：

```dotenv
DOMJUDGE_URL=https://judge.example.edu
API_USER=admin
API_PASS=your-password
DATA_DIR=rosters
OUTPUT_DIR=generated
```

`--env` 優先於環境變數 `CCUDJ_ENV_FILE`；兩者均未指定時，會從執行目錄向上尋找
`.env`。作業系統環境變數優先於檔案中的同名設定，載入檔案不會修改程序環境。

有選定設定檔時，`DATA_DIR` 與 `OUTPUT_DIR` 的相對路徑以該設定檔所在目錄為準。
未設定 `OUTPUT_DIR` 時，匯入檔仍寫回 `DATA_DIR`，保留舊用法。
命令列的 `--data-dir` 與 `--output-dir` 則以執行目錄為準，並優先於設定檔。

```powershell
ccudj --env ../course-data/115-1/.env setup
ccudj teams --env ../course-data/115-1/.env --data-dir ../course-data/115-1/rosters --output-dir ../course-data/115-1/generated
```

`groups`、`teams`、`accounts`、`setup` 都支援這些選項；
`python create_groups.py` 等舊入口也可使用相同選項。這些名單指令仍會實際上傳。

### 題目存放位置與顯示題名

題目資料夾名稱與顯示題名可分開指定：

```powershell
ccudj problem new new-problem --output-dir ../problem-bank/problems --title "A New Problem" --timelimit 1 --memory 256
```

這會建立 `../problem-bank/problems/new-problem/`，並將題名寫為 `A New Problem`。
原本的 `ccudj problem new hello 2 512` 與直接指定完整資料夾路徑的用法仍可使用；
未指定 `--title` 時，題名使用資料夾名稱，不包含父目錄路徑。

### 只檢查題目與指定 ZIP 輸出目錄

```powershell
ccudj problem upload ../problem-bank/problems/new-problem --validate-only
ccudj --env ../course-data/115-1/.env problem upload ../problem-bank/problems/new-problem --output-dir ../problem-bank/dist --save
```

`--validate-only` 檢查題本、C 參考解答是否存在與測資配對，支援遞迴檢查測資子目錄，
不讀取 API 帳密、不建立 ZIP、不發送請求。編譯、答案與測資範圍的驗證由各題的驗證程式負責。
上傳使用全域題目 API，建立題目後不會自動連結 contest。

題目 ZIP 只收根目錄的 `problem.html/pdf/txt`、`problem.yaml`、`domjudge-problem.ini`，
以及 `data/`、`submissions/`、`input_validators/`、`output_validators/`、
`include/`、`attachments/`、`problem_statement/`。
`data/` 內只收 `.in`、`.ans` 與 `testdata.yaml`。
本機 `.env*`、`*.env`、編譯產物、快取、符號連結與 ZIP 本身會排除；
題本資源請依題目格式放在支援的目錄中，獨立 HTML 可直接使用。

若工具專案搬到新路徑，請在新位置重建虛擬環境並重新安裝：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e .
```

啟用新的虛擬環境後即可繼續使用 `ccudj`；不建議直接沿用搬動前的 `.venv`。

## 專案架構

```text
src/domjudge_tools/
├── cli.py                 # ccudj 指令入口
├── config.py              # .env 與設定
├── api_client.py          # DOMjudge HTTP 共用邏輯
├── roster/
│   ├── groups.py
│   ├── teams.py
│   ├── accounts.py
│   └── setup.py
└── problem/
    ├── generator.py
    └── uploader.py
```

功能依領域分類，每支 `.py` 只負責一項工作。根目錄舊程式是相容入口；核心
測試放在 `tests/`，GitHub Actions 會在 push 與 pull request 時執行測試。

## 開發

```powershell
python -m unittest discover -v
```
