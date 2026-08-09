- 対話、ドキュメントは日本語で出力すること。ソースコード内のコメントは英語で記載すること。
- 処理を行った際に、未決の事項や先送りした事項がある場合は、docs/todo.mdに記載すること。

## プロジェクトドキュメント構成

| ファイル | 役割 | 主な読者 |
|---|---|---|
| [README.md](README.md) | 利用者向けの概要・インストール手順・使い方 | 利用者 |
| [requirement.md](docs/requirement.md) | 要件定義（実行形式・処理内容・技術要件） | 開発者 |
| [spec.md](docs/spec.md) | 設計書（`requirement.md` を入力とするモジュール設計・処理フロー・データ設計・テスト設計） | 開発者 |
| [plan.md](docs/plan.md) | 実装計画書（`spec.md` を入力とする関数単位のボトムアップ実装ステップ） | 開発者 |
| [todo.md](docs/todo.md) | 実装・動作確認で判明した未決事項の記録 | 開発者 |

## 開発工程と依存関係

ドキュメント間は上流から下流への一方向の依存関係を持つ。上流を変更した場合は下流の内容に矛盾がないか確認し、乖離があれば下流を更新すること。

```
requirement.md（要件定義）
      ↓ 入力とする
spec.md（設計書）
      ↓ 入力とする
plan.md（実装計画・Step 0〜10）
      ↓ 実施する
実装・テスト（src/, tests/）
      ↓ 整備する
README.md（利用者向けドキュメント）
      ↓ 構成する
CI設定（.github/workflows/test.yml）
```

- **requirement.md → spec.md**: 要件の変更はまず `requirement.md` に反映し、その後 `spec.md` の該当章を見直す。
- **spec.md → plan.md**: 設計変更が実装計画に影響する場合は `plan.md` の該当Stepを見直す。
- **plan.md → 実装/テスト**: `plan.md` の各Stepは前のStepの成果物に依存するため、原則Step 0から順に進める（完了条件はテストがgreenであること）。
- **実装 → README.md**: 実装中に `spec.md` との乖離が判明した場合は `spec.md` を更新し、利用者向けの使い方は `README.md` に反映する。
- **未決事項**: 対応方針が決まらない事項は `todo.md` に記録し、ヒアリング等で解消した際は `requirement.md`/`spec.md`/`plan.md`側に反映したうえで `todo.md` から除去する。
