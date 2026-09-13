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

完成 `problem.pdf`、`AC.c` 與至少一組同名 `.in`／`.ans` 後，可執行原有的
驗證、打包與上傳流程：

```powershell
ccudj problem upload hello
```

此指令也支援原有的 `--AC`、`--pdf`、`--save` 選項。

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
