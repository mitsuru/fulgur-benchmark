# fulgur-benchmark

fulgur / fullbleed / WeasyPrint を外部CLIとして比較するベンチマークスクリプト。

## 前提条件

- Python 3.10+
- 比較対象のツールが `PATH` にインストール済みであること（未インストールのツールはスキップされます）

## 使い方

```bash
# ベンチマーク実行
python benchmark.py

# 計測回数を変更
python benchmark.py --runs 10 --warmup 2
```

## 出力

- **stdout**: Markdownテーブル形式のサマリ
- **results/benchmark-YYYY-MM-DD.json**: 詳細なJSON結果

## テスト用HTML生成のみ

```bash
python -m templates.generate
```

## ライセンス

fulgurリポジトリ（AGPL）とは独立したリポジトリです。
