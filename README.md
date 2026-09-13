# DOMjudge 帳號匯入工具

[繁體中文](README.md) | [English](README.en.md)

這組工具可從 CSV 名單建立 DOMjudge 的 groups、teams 與使用者帳號，也能建立
DOMjudge 題目骨架，適用於 DOMjudge 9.0.0。`examples/` 內的範例名單皆為虛構
資料，可以安全地複製後使用。

## 安裝與設定

先安裝相依套件，接著將 `.env.example` 複製為 `.env`，填入 DOMjudge 網址與
API 帳號密碼。`DATA_DIR` 應指向存放 CSV 名單的資料夾；未設定時會使用目前
資料夾。

CSV 第一列必須是 `name,id`，後面可以有 `email` 等額外欄位。除了 `TA.csv`
之外，每個 CSV 檔名都代表一個學生 group；`TA.csv` 則用來建立管理員帳號。

```sh
python -m pip install -r requirements.txt
```

請將真實名單放在設定的資料目錄中。所有位置的 CSV、`.env`、產生的匯入檔案
與 Python 快取都已設定為不會加入 Git。只有 `examples/` 第一層的虛構 CSV
範例不受此限制；請勿把真實名單放進 `examples/`。

## 匯入指令

以下指令都能獨立執行。每支程式會先在 `DATA_DIR` 寫出可供檢查的檔案；如果
有資料，接著就會送出真正的 API 匯入請求。若想先檢查內容而不上傳，請使用
下一節的「只產生檔案」方式。

| 指令 | 產生的檢查檔案 | API 動作 |
| --- | --- | --- |
| `python create_groups.py` | `groups.json` | 建立 DOMjudge groups。 |
| `python create_teams.py` | `teams.json` | 為非 TA 名單中的學生建立 teams。 |
| `python create_accounts.py` | `accounts.yaml` | 為學生建立 team accounts，為 TA 建立 admin accounts。 |
| `python setup_domjudge.py` | 上傳前先產生全部三個檔案。 | 使用同一個連線依序匯入 groups、teams、accounts。 |

個別匯入程式不是預覽模式：寫出檢查檔案後，就會向設定的 DOMjudge API
送出真正的匯入請求。`setup_domjudge.py` 會先建立全部資料內容，因此名單遺失、
無法讀取或格式錯誤時，不會送出任何 API 請求。確認無誤後才會依相依順序上傳；
任一階段失敗就不再執行後續階段。

## 只產生檔案，不上傳

在 repository 目錄執行 `python`，輸入以下程式。請將 `data_dir` 改為實際的
名單資料夾，也就是 `.env` 中 `DATA_DIR` 所使用的路徑。這些 generate/save
函式不需要 API 帳密，也不會發出網路請求。

```python
from pathlib import Path
from create_groups import generate_groups, save_groups
from create_teams import generate_teams, save_teams
from create_accounts import generate_accounts, save_accounts

data_dir = Path("rosters/fall")
groups = generate_groups(data_dir)
teams = generate_teams(data_dir)
accounts = generate_accounts(data_dir)
save_groups(groups, data_dir / "groups.json")
save_teams(teams, data_dir / "teams.json")
save_accounts(accounts, data_dir / "accounts.yaml")
```

`teams.json` 會為非 TA CSV 中的每位學生建立一個 team，CSV 檔名會成為
group ID：

```json
[
  {
    "id": "S100001",
    "group_ids": ["CAT"],
    "name": "Ada Example"
  }
]
```

`accounts.yaml` 會包含學生帳號與 TA 帳號。學生帳號會綁定相同 ID 的 team：

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

TA admin account 不會指定 `team_id`；DOMjudge 9.0.0 會自動建立並綁定管理員
使用的隱藏 Jury team。

請先在本機檢查這三個檔案。確認後設定 API 帳密並執行
`python setup_domjudge.py`，程式會依目前 CSV 重新建立內容並執行真正的匯入。
若要確保上傳內容與檢查過的內容相同，請不要在兩次操作之間修改 CSV。

## 產生題目骨架

`gen_problem.py` 會建立 DOMjudge 題目目錄，但不會上傳任何資料。可以使用位置
參數：

```powershell
python gen_problem.py hello 2 512
```

也可以使用具名參數，效果相同：

```powershell
python gen_problem.py --name hello --timelimit 2 --memory 512
```

參數依序代表題目名稱、時間限制（秒）與記憶體限制（MiB）。若省略時間或記憶體，
預設值分別為 `1.0` 秒與 `256` MiB。

上述指令會建立：

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

`problem.yaml` 保存名稱、輸出比對設定與記憶體限制：

```yaml
name: hello
validator_flags: case_sensitive space_change_sensitive
limits:
  memory: 512
```

DOMjudge 9.0.0 的時間限制寫入 `domjudge-problem.ini`：

```ini
name = hello
timelimit = 2.0
```

產生骨架後，請完成以下內容：

1. 將正式解答寫入 `submissions/accepted/AC.c`。
2. 將題目敘述放在題目目錄的 `problem.pdf`。
3. 在 `data/sample/` 或 `data/secret/` 放入至少一組同名的 `.in` 與 `.ans`。

這一節只說明題目骨架產生；現有 `upload_problem.py` 的行為未在本次調整。
