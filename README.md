# tmpl

`~/share/tmpl/[種類]` に配置したJinja2ベースのテンプレートディレクトリから、新規プロジェクトの初期ディレクトリ構成・ファイルを生成するCLIツール。

詳細な要件・設計は [requirement.md](docs/requirement.md) / [spec.md](docs/spec.md) を参照。

## インストール

```
pip install -e ".[test]"
```

`tmpl` コマンド（`[project.scripts]` で登録）または `python -m tmpl` として実行できる。

## 使い方

```
tmpl [種類] [プロジェクト名] [-o/--output 出力先] [--verbose] [--dry-run] [変数名=値 ...]
```

例:

```
tmpl python-cli myapp author=alice -o ./projects/myapp
```

- `種類`: `~/share/tmpl/[種類]` に配置されたテンプレートディレクトリを選択する
- `プロジェクト名`: テンプレート内で `{{ project_name }}` として参照できる
- `-o`, `--output`: 出力先ディレクトリ（省略時はカレントディレクトリ直下に `プロジェクト名` のディレクトリを作成）
- `--verbose`: 展開した各ファイル・ディレクトリのパスを表示する
- `--dry-run`: 実際には書き込まず、展開されるパスのみを表示する
- `変数名=値`: テンプレート内で `{{ 変数名 }}` として参照できる任意の変数を指定する（ファイル内容・ファイル名・ディレクトリ名のいずれにも使用可能）

テンプレートディレクトリ内の `.git`, `__pycache__`, `.DS_Store` 等は展開対象から除外される（詳細は [spec.md](docs/spec.md) の除外パターン参照）。

## テスト

```
pip install -e ".[test]"
pytest
```
