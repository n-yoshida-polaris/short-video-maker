"""
Multi-channel runner for ShortVideoMaker.

channels/ ディレクトリ（または --channels-dir で指定したディレクトリ）に置かれた
*.yaml / *.yml ファイルをファイル名昇順で読み込み、順番に svmu.main.run() を実行します。

使用例:
  python -m svmu_multi.run                        # 通常実行
  python -m svmu_multi.run --dry-run              # ファイル一覧のみ（処理しない）
  python -m svmu_multi.run --limit 3              # チャンネルあたり最大3件
  python -m svmu_multi.run --channels-dir ./my_ch # ディレクトリ指定
"""
from __future__ import annotations

import argparse
import glob as _glob
import os

from svmu.main import run as svmu_run


def _find_channel_yamls(channels_dir: str) -> list[str]:
    """channels_dir 直下の *.yaml / *.yml をファイル名昇順で返す。"""
    files = sorted(
        _glob.glob(os.path.join(channels_dir, "*.yaml"))
        + _glob.glob(os.path.join(channels_dir, "*.yml"))
    )
    # sample ファイルはスキップ
    return [f for f in files if not os.path.basename(f).startswith("channel.sample")]


def main():
    parser = argparse.ArgumentParser(
        description="Multi-channel ShortVideoMaker runner"
    )
    parser.add_argument(
        "--channels-dir", default="./channels",
        help="チャンネル YAML を置いたディレクトリ (default: ./channels)",
    )
    parser.add_argument(
        "--limit", type=int, default=10,
        help="チャンネルあたりの最大処理件数 (default: 10)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="チャンネル一覧を表示するだけで処理しない",
    )
    args = parser.parse_args()

    channels_dir = args.channels_dir
    if not os.path.isdir(channels_dir):
        print(f"[ERROR] channels-dir が見つかりません: {channels_dir}")
        return

    yamls = _find_channel_yamls(channels_dir)
    if not yamls:
        print(f"[INFO] YAML ファイルが見つかりません: {channels_dir}")
        return

    print(f"[INFO] {len(yamls)} チャンネルが見つかりました ({channels_dir}):")
    for y in yamls:
        print(f"  {y}")

    if args.dry_run:
        print("[DRY-RUN] --dry-run 指定のため処理をスキップします。")
        return

    total = 0
    errors = 0
    for yaml_path in yamls:
        print(f"\n{'=' * 60}")
        print(f"[CHANNEL] {yaml_path}")
        print(f"{'=' * 60}")
        try:
            n = svmu_run(config_yaml=yaml_path, limit=args.limit)
            total += n
        except Exception as e:
            print(f"[ERROR] チャンネル処理に失敗しました: {e}")
            errors += 1

    print(
        f"\n[MULTI-DONE] 合計 {total} 件処理完了 "
        f"({len(yamls)} チャンネル中 {errors} チャンネルでエラー)"
    )


if __name__ == "__main__":
    main()
