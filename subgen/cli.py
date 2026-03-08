"""CLIエントリーポイント"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from subgen import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="subgen",
        description="SubGen - 動画字幕自動生成ツール (Moonshine ASR + 翻訳API)",
    )
    parser.add_argument("input", help="入力動画ファイル (MP4)")
    parser.add_argument("--version", action="version", version=f"subgen {__version__}")
    parser.add_argument("-l", "--lang", default="ja", help="音声の言語 (デフォルト: ja)")
    parser.add_argument(
        "-f", "--format", default="ass",
        choices=["srt", "ass", "both"],
        help="出力形式 (デフォルト: ass)",
    )
    parser.add_argument("-o", "--output", default=None, help="出力先ディレクトリ")
    parser.add_argument("-t", "--translate", default=None, help="翻訳先言語 (例: zh, en)")
    parser.add_argument("--api", default="deepl", choices=["deepl", "google"], help="翻訳API (デフォルト: deepl)")
    parser.add_argument("--speakers", default="auto", help="話者数 (auto / 1 / 2 / 3 ...)")
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細ログ出力")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"エラー: 入力ファイルが見つかりません: {input_path}", file=sys.stderr)
        return 1

    # 話者数パラメータの処理
    num_speakers = args.speakers
    if num_speakers != "auto":
        try:
            num_speakers = int(num_speakers)
            if num_speakers < 1:
                raise ValueError
        except ValueError:
            print(f"エラー: --speakers は 'auto' または正の整数を指定してください", file=sys.stderr)
            return 1

    from subgen.pipeline import run

    try:
        files = run(
            video_path=input_path,
            output_dir=args.output,
            language=args.lang,
            format=args.format,
            translate_to=args.translate,
            translate_api=args.api,
            num_speakers=num_speakers,
            verbose=args.verbose,
        )

        if files:
            print(f"\n生成完了: {len(files)} ファイル")
            for f in files:
                print(f"  {f}")
        else:
            print("字幕を生成できませんでした。", file=sys.stderr)
            return 1

    except FileNotFoundError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1
    except ImportError as e:
        print(f"依存関係エラー: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
