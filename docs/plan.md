# 実装計画書 (plan.md)

`spec.md` を入力とした `tmpl` コマンドの実装計画。関数単位で「実装→テスト」を積み上げるボトムアップの進め方とする。各ステップは前のステップの成果物に依存するため、原則上から順に進める。

## 1. 進め方の方針

- 依存の少ないモジュール（`exceptions.py`, `constants.py`）から着手し、`generator.py` は spec.md 3.2章の小さい関数単位で実装とテストをセットで進める。
- `generator.py` が一通り動作してから `cli.py` を実装し、最後に結合・手動動作確認を行う。
- 各ステップの完了条件（DoD）は「対応するテストが green であること」を基本とする。

## 2. 作業ステップ

### Step 0: プロジェクト雛形の作成

- [ ] spec.md 2.1章のディレクトリ構成で `src/tmpl/`, `tests/` を作成し、各モジュールの空ファイルを配置する
- [ ] `pyproject.toml` を作成する（spec.md 2.2章: `requires-python>=3.11`, 依存 `jinja2`, dev依存 `pytest`, `[project.scripts] tmpl = "tmpl.cli:main"`）
- [ ] `pip install -e ".[test]"`（または相当のコマンド）でインストールできることを確認する
- [ ] `pytest` が空の状態で実行できることを確認する

DoD: `pip install -e .` が成功し、`tmpl --help` は未実装のためエラーで構わないが、パッケージとして import できる状態になっていること。

### Step 1: `exceptions.py`

- [ ] spec.md 3.3章の例外クラス（`TmplError`, `TemplateNotFoundError`, `OutputExistsError`, `InvalidInstructionError`）を実装する

DoD: 各クラスが `TmplError` を継承していることをテストで確認する。

### Step 2: `constants.py`

- [ ] `DEFAULT_EXCLUDE_PATTERNS`（spec.md 3.4章）を実装する

### Step 3: `generator.py`（基盤関数）

小さい関数から順に実装し、都度 `tests/test_generator.py` にテストを追加する（spec.md 6.2章の観点に対応）。

- [ ] `resolve_template_dir(kind)` を実装（`Path.home()` は `monkeypatch` で差し替えてテスト）
  - [ ] テンプレートディレクトリが存在しない場合に `TemplateNotFoundError` を送出するテスト
- [ ] `resolve_output_dir(project_name, output)` を実装
  - [ ] 出力先が既存の場合に `OutputExistsError` を送出するテスト
  - [ ] `output` 省略時にカレントディレクトリ直下の `project_name` を返すテスト
- [ ] `build_jinja_env()` を実装（`StrictUndefined`, `keep_trailing_newline=True`）
- [ ] `is_excluded(path, root)` を実装
  - [ ] `.git` 等のデフォルト除外パターンに一致判定されるテスト
- [ ] `render_path(env, src, template_dir, output_dir, context)` を実装
  - [ ] ファイル名・ディレクトリ名に含まれる `{{ project_name }}` 等が置換されるテスト

### Step 4: `generator.py`（ファイル書き込み系）

- [ ] `copy_or_render_file(env, src, dst, context)` を実装
  - [ ] テキストファイルの内容が Jinja2 でレンダリングされるテスト
  - [ ] バイナリファイル（UTF-8デコード不能）がレンダリングされずそのままコピーされるテスト
- [ ] `copy_symlink(src, dst)` を実装
  - [ ] シンボリックリンクがリンクとして複製される（リンク先が解決されない）テスト。`platform.system() == "Windows"` の場合は `pytest.mark.skipif` でスキップする（spec.md 6.2章）
  - [ ] Windows で権限不足により `OSError` が発生した場合に `TmplError` へラップされることのテストは、CIのWindowsランナーでは前提が成立しないためスキップ対象とし、Step 8 の手動確認で代替する
- [ ] `report(verbose, dry_run, src, dst)` を実装
  - [ ] `verbose=True` または `dry_run=True` の場合に標準出力へ表示されるテスト（`capsys` を使用）

### Step 5: `generator.py`（結合）

- [ ] `render_tree(template_dir, output_dir, context, verbose, dry_run)` を実装（spec.md 3.2章の疑似コードに準拠、`os.walk(followlinks=False)` で走査）
  - [ ] ファイル内容・ファイル名・ディレクトリ名が正しくレンダリングされる統合テスト
  - [ ] 除外パターンに一致するディレクトリの配下が走査されない（除外ディレクトリの中身がコピーされない）テスト
  - [ ] 未定義変数を参照するテンプレートで `TmplError` が送出されるテスト
  - [ ] `dry_run=True` の場合に実際のファイル・ディレクトリが作成されないテスト
- [ ] `generate_project(kind, project_name, output, variables, verbose, dry_run)` を実装（`resolve_template_dir` → `resolve_output_dir` → `render_tree` を結線）
  - [ ] 正常系の結合テスト（サンプルテンプレートディレクトリを `tmp_path` に用意して実行し、出力を検証）

DoD: `tests/test_generator.py` が spec.md 6.2章の全観点をカバーし green であること。

### Step 6: `cli.py`

- [ ] `parse_args(argv)` を実装（`kind`, `project_name`, `instructions`（`nargs="*"`）, `-o/--output`, `--verbose`, `--dry-run`）
  - [ ] 必須引数（`kind`, `project_name`）欠落時に `argparse` がエラー終了するテスト
- [ ] `parse_instructions(instructions)` を実装（最初の `=` で分割、`project_name` キーは無視して呼び出し元の値を優先）
  - [ ] `変数名=値` 形式でない要素で `InvalidInstructionError` を送出するテスト
- [ ] `main(argv)` を実装（`generate_project` 呼び出し、`TmplError` 捕捉、exit code 制御）
  - [ ] 異常系（`TmplError` 発生）で exit code 1・標準エラー出力にメッセージが出るテスト
  - [ ] `--dry-run` 指定時、実際にファイルが作成されないことをCLI経由で確認するテスト
  - [ ] `--verbose` 指定時、展開対象パスがログ出力されることを確認するテスト（`capsys`）

DoD: `tests/test_cli.py` が spec.md 6.1章の全観点をカバーし green であること。

### Step 7: `__main__.py` とエントリポイントの疎通確認

- [ ] `__main__.py` に `python -m tmpl` 用のエントリを実装（`sys.exit(main())`）
- [ ] `pip install -e .` 後、`tmpl` コマンドとして実行できることを確認する
- [ ] `python -m tmpl` でも同様に実行できることを確認する

### Step 8: 手動動作確認

- [ ] `~/share/tmpl/sample` にサンプルテンプレート（テキストファイル・バイナリファイル・除外対象ファイル・シンボリックリンクを含む）を用意する
- [ ] `tmpl sample myproj key=value` を実行し、出力先ディレクトリの内容を目視確認する
- [ ] `-o` オプションで出力先を指定して実行し、動作を確認する
- [ ] `--dry-run` を指定し、ファイルが作成されずログのみ表示されることを確認する
- [ ] `--verbose` を指定し、詳細ログが表示されることを確認する
- [ ] 出力先が既に存在する場合にエラーで終了することを確認する
- [ ] テンプレートディレクトリが存在しない `種類` を指定した場合にエラーで終了することを確認する
- [ ] 未定義変数を参照するテンプレートを用意し、エラーで終了することを確認する
- [ ] （実行環境で可能であれば）シンボリックリンクを含むテンプレートを展開し、リンクとして複製されることを確認する。Windowsで権限エラーになる場合は、エラーメッセージが適切に表示されることを確認する

### Step 9: ドキュメント整備

- [ ] `README.md` を作成し、インストール方法・実行方法・オプション一覧を記載する
- [ ] `spec.md` との差異が生じていないか最終確認する（実装中に判明した設計との乖離があれば `spec.md` を更新する）

### Step 10: CI設定（GitHub Actions）

- [ ] `.github/workflows/test.yml` を作成し、`ubuntu-latest` / `windows-latest` / `macos-latest` のマトリクスで `pytest` を実行するワークフローを構成する（spec.md 6.3章）
- [ ] `pip install -e ".[test]"` 相当のセットアップ手順をワークフローに含める
- [ ] Windows ランナーでシンボリックリンク関連テストが `skip` 扱いになり、それ以外のテストが green になることを確認する
- [ ] push・PR をトリガーに実行されることを確認する

## 3. 全体の完了条件

- `pytest` が全てgreenであること（spec.md 6章の全観点を網羅、Windowsでのシンボリックリンク関連テストは仕様通りskipされること）
- Step 8 の手動動作確認が全て完了していること
- `tmpl` コマンドおよび `python -m tmpl` の両方でエントリポイントが動作すること
- Step 10 のCIワークフローが3OSすべてで正常に実行されること

## 4. リスク・注意点

- Windows でのシンボリックリンク作成は権限（開発者モードまたは管理者権限）に依存する。GitHub Actions の `windows-latest` ランナーでは標準で権限がないため、該当テストは `skipif` でスキップし、実際の権限エラー時の挙動はStep 8の手動確認で担保する。
- バイナリ判定はUTF-8デコード可否による簡易判定のため、UTF-8として偶然デコード可能なバイナリファイルは誤ってテキストとして処理される可能性がある（spec.mdの設計上の制約であり、本計画のスコープでは対応しない）。
