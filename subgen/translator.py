"""F-004: 翻訳モジュール（DeepL / Google Cloud Translation）"""

from __future__ import annotations

import os
from dataclasses import replace

from subgen.asr import Segment


def translate_segments(
    segments: list[Segment],
    target_lang: str = "zh",
    source_lang: str = "ja",
    api: str = "deepl",
    verbose: bool = False,
) -> list[Segment]:
    """セグメントリストを翻訳する。

    Args:
        segments: 翻訳元のセグメントリスト
        target_lang: 翻訳先言語コード
        source_lang: 翻訳元言語コード
        api: 使用するAPI（"deepl" または "google"）
        verbose: 詳細ログ出力

    Returns:
        翻訳されたテキストを持つ新しいSegmentのリスト
    """
    if not segments:
        return []

    texts = [seg.text for seg in segments]

    if api == "deepl":
        translated = _translate_deepl(texts, target_lang, source_lang, verbose)
    elif api == "google":
        translated = _translate_google(texts, target_lang, source_lang, verbose)
    else:
        raise ValueError(f"不明な翻訳API: {api}。'deepl' または 'google' を指定してください。")

    result = []
    for seg, trans_text in zip(segments, translated):
        result.append(replace(seg, text=trans_text))

    if verbose:
        print(f"[翻訳] {len(result)} セグメントを {source_lang} → {target_lang} に翻訳完了")

    return result


def _translate_deepl(
    texts: list[str],
    target_lang: str,
    source_lang: str,
    verbose: bool,
) -> list[str]:
    """DeepL APIで翻訳する。"""
    api_key = os.environ.get("DEEPL_API_KEY")
    if not api_key:
        raise ValueError(
            "DEEPL_API_KEYが設定されていません。\n"
            "環境変数 DEEPL_API_KEY にAPIキーを設定してください。"
        )

    # DeepLの言語コードマッピング
    lang_map = {"zh": "ZH", "en": "EN-US", "ja": "JA", "ko": "KO"}
    dl_target = lang_map.get(target_lang, target_lang.upper())
    dl_source = lang_map.get(source_lang, source_lang.upper())

    try:
        import deepl

        translator = deepl.Translator(api_key)
        if verbose:
            print(f"[翻訳] DeepL APIで {len(texts)} テキストを翻訳中...")

        results = []
        # バッチ処理（DeepLは最大50件ずつ）
        batch_size = 50
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = translator.translate_text(
                batch,
                source_lang=dl_source,
                target_lang=dl_target,
            )
            if isinstance(response, list):
                results.extend([r.text for r in response])
            else:
                results.append(response.text)

        return results

    except ImportError:
        # deepl パッケージなし → REST APIを直接呼ぶ
        return _translate_deepl_rest(texts, dl_target, dl_source, api_key, verbose)


def _translate_deepl_rest(
    texts: list[str],
    target_lang: str,
    source_lang: str,
    api_key: str,
    verbose: bool,
) -> list[str]:
    """DeepL REST APIを直接呼び出す。"""
    import requests

    # Free APIかPro APIか判定
    if api_key.endswith(":fx"):
        base_url = "https://api-free.deepl.com/v2/translate"
    else:
        base_url = "https://api.deepl.com/v2/translate"

    if verbose:
        print(f"[翻訳] DeepL REST APIで {len(texts)} テキストを翻訳中...")

    results = []
    batch_size = 50
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = requests.post(
            base_url,
            headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
            json={
                "text": batch,
                "source_lang": source_lang,
                "target_lang": target_lang,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        results.extend([t["text"] for t in data["translations"]])

    return results


def _translate_google(
    texts: list[str],
    target_lang: str,
    source_lang: str,
    verbose: bool,
) -> list[str]:
    """Google Cloud Translation APIで翻訳する。"""
    try:
        from google.cloud import translate_v2 as translate
    except ImportError:
        raise ImportError(
            "google-cloud-translate がインストールされていません。\n"
            "pip install google-cloud-translate でインストールしてください。"
        )

    # GOOGLE_APPLICATION_CREDENTIALS環境変数が必要
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        raise ValueError(
            "GOOGLE_APPLICATION_CREDENTIALS が設定されていません。\n"
            "サービスアカウントキーのJSONファイルパスを環境変数に設定してください。"
        )

    if verbose:
        print(f"[翻訳] Google Cloud Translation APIで {len(texts)} テキストを翻訳中...")

    client = translate.Client()
    results = []

    # バッチ処理（128件ずつ）
    batch_size = 128
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = client.translate(
            batch,
            target_language=target_lang,
            source_language=source_lang,
            format_="text",
        )
        results.extend([r["translatedText"] for r in response])

    return results
