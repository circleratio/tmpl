# 設計書 (spec.md)

`requirement.md` を入力とした `tmpl` コマンドの設計書。

## 1. 概要

`tmpl` は、`~/share/tmpl/[種類]` に配置されたテンプレートディレクトリを Jinja2 でレンダリングしながら指定の出力先へ展開し、新規プロジェクトの初期構成を作成する CLI コマンドである。

## 2. システム構成

### 2.1 リポジトリのディレクトリ構成

pip でインストール可能な src レイアウトのパッケージとする。

```
tmpl/
├── pyproject.toml
├── README.md
├── requirement.md
├── spec.md
├── todo.md
├── src/
│   └── tmpl/
│       ├── __init__.py
│       ├── __main__.py      # `python -m tmpl` 用エントリポイント
│       ├── cli.py           # 引数パース・エントリポイント (main)
│       ├── generator.py     # テンプレート展開のコア処理
│       ├── exceptions.py    # 例外クラス定義
│       └── constants.py     # デフォルト除外パターン等の定数
└── tests/
    ├── test_cli.py
    └── test_generator.py
```

### 2.2 pyproject.toml 概要

- ビルドバックエンド: `setuptools.build_meta`
- `requires-python`: `>=3.11`
- 依存パッケージ: `jinja2`
- 開発用依存パッケージ（`[project.optional-dependencies]` の `test` グループ等）: `pytest`
- エントリポイント: `[project.scripts]` に `tmpl = "tmpl.cli:main"` を登録し、`pip install .` 後に `tmpl` コマンドとして実行可能にする
- 対応OS: Windows / Linux / macOS。パス操作はすべて `pathlib.Path` を用い、OS固有の区切り文字に依存しないようにする

## 3. モジュール設計

### 3.1 `cli.py`

コマンドライン引数の解析とエントリポイントを担う。CLI引数パーサーは標準ライブラリの `argparse` を用いる（追加依存を増やさないため）。

- 位置引数
  - `kind`: テンプレートの種類（必須）
  - `project_name`: プロジェクト名（必須）
  - `instructions`: `nargs="*"` で可変長に受け取る `変数名=値` 形式の文字列群（任意）
- オプション引数
  - `-o`, `--output`: 出力先ディレクトリのパス（任意、省略時はカレントディレクトリ直下に `project_name` のディレクトリを作成）
  - `--verbose`: 指定時、展開した各ファイル・ディレクトリのパスを標準出力に逐次表示する（`store_true`）
  - `--dry-run`: 指定時、実際のディレクトリ作成・ファイル書き込みを行わず、展開対象のパス一覧のみを標準出力に表示する（`store_true`）

```python
def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    args = parse_args(argv)
    try:
        variables = parse_instructions(args.instructions)
        generate_project(
            kind=args.kind,
            project_name=args.project_name,
            output=args.output,
            variables=variables,
            verbose=args.verbose,
            dry_run=args.dry_run,
        )
    except TmplError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0
```

`parse_instructions` は各要素を最初の `=` で分割して `dict[str, str]` を構築する。`=` を含まない要素があった場合は `InvalidInstructionError` を送出する。`project_name` というキーが `instructions` 側で重複指定された場合はエラーとせず、`project_name` 引数の値を優先する。

### 3.2 `generator.py`

テンプレート展開のコア処理を担う。

- `resolve_template_dir(kind: str) -> Path`
  `Path.home() / "share" / "tmpl" / kind` を返す。存在しない、またはディレクトリでない場合は `TemplateNotFoundError` を送出する。

- `resolve_output_dir(project_name: str, output: str | None) -> Path`
  `output` が指定されていればそのパスを、未指定であればカレントディレクトリ直下の `project_name` を返す。返すパスが既に存在する場合は `OutputExistsError` を送出する。

- `generate_project(kind: str, project_name: str, output: str | None, variables: dict[str, str], verbose: bool = False, dry_run: bool = False) -> None`
  上記2関数で入出力パスを解決した後、`render_tree` を呼び出す。

- `render_tree(template_dir: Path, output_dir: Path, context: dict, verbose: bool = False, dry_run: bool = False) -> None`
  `template_dir` を再帰的に走査し、`output_dir` 配下に展開する。シンボリックリンクされたディレクトリを実ディレクトリとして二重に辿らないよう、`Path.rglob` ではなく `os.walk(template_dir, followlinks=False)` を用いて明示的に走査する。

```python
def render_tree(
    template_dir: Path,
    output_dir: Path,
    context: dict,
    verbose: bool = False,
    dry_run: bool = False,
) -> None:
    env = build_jinja_env()
    if not dry_run:
        output_dir.mkdir(parents=True)

    for dirpath, dirnames, filenames in os.walk(template_dir, followlinks=False):
        src_dir = Path(dirpath)
        # Do not descend into excluded directories (e.g. .git, __pycache__).
        dirnames[:] = [d for d in dirnames if not is_excluded(src_dir / d, template_dir)]

        # os.walk(followlinks=False) lists symlinked directories in dirnames
        # without recursing into them, so each entry is visited exactly once.
        for name in dirnames + filenames:
            src = src_dir / name
            if is_excluded(src, template_dir):
                continue
            dst = render_path(env, src, template_dir, output_dir, context)
            report(verbose, dry_run, src, dst)
            if dry_run:
                continue
            if src.is_symlink():
                copy_symlink(src, dst)
            elif src.is_dir():
                dst.mkdir(parents=True, exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                copy_or_render_file(env, src, dst, context)
```

- `build_jinja_env() -> jinja2.Environment`
  `Environment(undefined=jinja2.StrictUndefined, keep_trailing_newline=True)` を返す。テンプレートファイルはディスク上のディレクトリをそのまま走査するため `FileSystemLoader` は使わず、ファイル内容・パス名それぞれを文字列として `env.from_string(...).render(...)` する。

- `render_path(env, src: Path, template_dir: Path, output_dir: Path, context: dict) -> Path`
  `src.relative_to(template_dir)` の各パス構成要素を Jinja2 でレンダリングし、`output_dir` を起点に結合したパスを返す。

- `copy_or_render_file(env, src: Path, dst: Path, context: dict) -> None`
  `src` を UTF-8 テキストとして読み込む。`UnicodeDecodeError` が発生した場合はバイナリファイルとみなし、`shutil.copy2` でそのままコピーする（レンダリングはファイル名のみに適用済み）。デコードに成功した場合はテキストとして Jinja2 でレンダリングし、UTF-8 で書き込む。

- `copy_symlink(src: Path, dst: Path) -> None`
  `os.readlink(src)` で取得したリンク先をそのまま使い、`os.symlink(target, dst, target_is_directory=src.is_dir())` でシンボリックリンクを複製する（リンク先の実体は解決しない）。Windows環境でシンボリックリンク作成に必要な権限（開発者モードまたは管理者権限）が無く `OSError` が発生した場合は `TmplError` にラップして送出し、異常終了する。

- `report(verbose: bool, dry_run: bool, src: Path, dst: Path) -> None`
  `verbose` または `dry_run` が真の場合、`dst`（dry-run時は「これから作成される」パス）を標準出力に1行ずつ表示する。

- `is_excluded(path: Path, root: Path) -> bool`
  `path` の各パス構成要素（`root` からの相対パス）が `constants.DEFAULT_EXCLUDE_PATTERNS` のいずれかに `fnmatch` するかを判定する。

### 3.3 `exceptions.py`

```python
class TmplError(Exception):
    """Base class for all tmpl errors."""

class TemplateNotFoundError(TmplError):
    """Raised when the template directory for the given kind does not exist."""

class OutputExistsError(TmplError):
    """Raised when the output path already exists."""

class InvalidInstructionError(TmplError):
    """Raised when an instruction argument is not in 'name=value' form."""
```

Jinja2 の `UndefinedError`（未定義変数参照時に `StrictUndefined` が送出する）は `render_tree` 内で捕捉し、`TmplError` でラップして再送出する。

### 3.4 `constants.py`

```python
# Directory/file name patterns excluded from template rendering (fnmatch against each path segment).
DEFAULT_EXCLUDE_PATTERNS = [
    ".git",
    "__pycache__",
    ".DS_Store",
    "*.pyc",
    ".venv",
    "node_modules",
    ".pytest_cache",
    ".mypy_cache",
]
```

## 4. 処理フロー

```
1. cli.main() が argv を parse_args() でパースする
2. parse_instructions() で instructions を dict[str, str] に変換する
   - "=" を含まない要素があれば InvalidInstructionError
3. generate_project() を呼び出す
   3.1 resolve_template_dir(kind)
       - ~/share/tmpl/[kind] が存在しなければ TemplateNotFoundError
   3.2 resolve_output_dir(project_name, output)
       - 解決したパスが既に存在すれば OutputExistsError
   3.3 context = {**variables, "project_name": project_name} を組み立てる（`variables` に `project_name` キーが含まれていても引数の値で上書きする）
   3.4 render_tree(template_dir, output_dir, context, verbose, dry_run)
       - テンプレートディレクトリを os.walk(followlinks=False) で走査（シンボリックリンクを実体として二重に辿らない）
       - 除外パターンに一致する要素・ディレクトリはスキップ（除外ディレクトリの配下は走査自体を行わない）
       - ディレクトリ/ファイル名を Jinja2 でレンダリングして出力先パスを決定
       - verbose または dry-run 指定時は、決定した出力先パスを標準出力に表示
       - dry-run 指定時はここでファイル・ディレクトリの実体を作成せず終了
       - シンボリックリンクはリンクとして複製、ディレクトリは作成、ファイルはテキストなら
         内容もレンダリングして書き込み、バイナリならそのままコピー
       - 未定義変数参照時は TmplError を送出
4. 正常終了時は exit code 0、TmplError 捕捉時は標準エラー出力にメッセージを表示し exit code 1
```

## 5. データ設計

### 5.1 変数コンテキスト

| キー | 由来 | 備考 |
|---|---|---|
| `project_name` | `project_name` 引数 | 固定変数。`instructions` 側で同名指定があっても引数の値を優先 |
| 任意の変数名 | `instructions` の `変数名=値` | 値は常に文字列として扱う |

### 5.2 終了コード

| コード | 意味 |
|---|---|
| 0 | 正常終了 |
| 1 | `TmplError` 系の異常終了（テンプレート未存在、出力先重複、指示形式不正、未定義変数参照など） |

## 6. テスト設計

`pytest` を用いた自動テストを `tests/` 配下に用意する。テストの実行は `pytest` コマンドで行う。`tmp_path` フィクスチャでテンプレートディレクトリ・出力先ディレクトリを作成し、`~/share/tmpl` は `monkeypatch` で `Path.home()` の戻り値を差し替えて参照させる。

### 6.1 `test_cli.py`

- 必須引数（`kind`, `project_name`）欠落時に `argparse` がエラー終了すること
- `変数名=値` 形式でない `instructions` を渡した場合に exit code 1・エラーメッセージが出力されること
- `--dry-run` 指定時、実際にはファイル・ディレクトリが作成されないこと
- `--verbose` 指定時、展開対象パスがログ出力されること

### 6.2 `test_generator.py`

- `resolve_template_dir` がテンプレート未存在時に `TemplateNotFoundError` を送出すること
- `resolve_output_dir` が出力先重複時に `OutputExistsError` を送出すること
- `render_tree` がファイル内容・ファイル名・ディレクトリ名を正しくレンダリングすること
- 未定義変数を参照するテンプレートで `TmplError` が送出されること
- `.git` 等の除外パターンに一致するファイル・ディレクトリがコピーされないこと
- バイナリファイル（UTF-8デコード不能なファイル）がレンダリングされずそのままコピーされること
- シンボリックリンクがリンクとして複製されること（リンク先が解決されないこと）。GitHub Actions の Windows ランナーは標準でシンボリックリンク作成権限を持たないため、このテストは `platform.system() == "Windows"` の場合 `pytest.mark.skipif` でスキップする

### 6.3 CI

GitHub Actions で `ubuntu-latest` / `windows-latest` / `macos-latest` の3OSに対するマトリクスビルドを構成し、push・PR時に `pytest` を自動実行する。

## 7. 対応範囲外・制約

- 出力先ディレクトリ内の一部ファイルのみの上書き・マージには対応しない（出力先パスが存在する時点で全体をエラーとする）。
- Windows でシンボリックリンクを含むテンプレートを展開する場合、実行ユーザーに開発者モードまたは管理者権限が必要になることがある（3.2章 `copy_symlink` 参照）。
