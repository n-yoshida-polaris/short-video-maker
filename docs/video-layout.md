# 動画レイアウト仕様

[`svmu/render_image.py`](../svmu/render_image.py) と [`svmu/compose_video.py`](../svmu/compose_video.py) で定義されている各要素のサイズ・配置・エフェクトを網羅します。

---

## キャンバス

| 項目 | 値 |
|:---|:---|
| 幅 | 1080 px |
| 高さ | 1920 px |
| アスペクト比 | 9:16（縦型） |
| ベース | 透明（RGBA）。背景動画へ合成 |
| SNS 非表示余白 | 左右各 50 px（YouTube/SNS 再生時に隠れる想定領域） |

```
←──────────────── 1080 px ────────────────→
┌─────────────────────────────────────────┐  ↑
│  50px│                           │50px  │  │
│      │                           │      │  │
│      │       タイトル            │      │  240 px (TITLE_Y)
│      │  （水平センタリング）      │      │  │
│      │                           │      │  ↓
│      ├───────────────────────────┤      │
│      │                           │      │  ↑
│      │ 箇条書き（X=90 左揃え）   │      │  │
│      │ 項目1                     │      │  560 px (BULLET_Y)
│      │ 項目2                     │      │  │
│      │   …                       │      │  ↓
│      │                           │      │
└─────────────────────────────────────────┘
       ←────── MAX 900 px ──────→
```

---

## タイトル

定義箇所: `render_image.py` 16〜22 行

| 項目 | デフォルト値 | 設定キー |
|:---|:---|:---|
| フォントサイズ | 92 px | — |
| 行間 | 1.3 ×（行の高さ） | — |
| 横揃え | センタリング | — |
| 開始 Y | 240 px | — |
| 開始 X（左揃え時のみ） | 90 px | — |
| 最大テキスト幅 | 900 px | — |
| 文字色 | `#FFFFFF`（白・不透明） | `TITLE_COLOR` |
| 影色 | `#000000B4`（黒・Alpha 180 ≈ 70%） | `TITLE_SHADOW` |
| 影オフセット | `(2, 2)` px | `SHADOW_OFFSET` |

- 900 px を超える文字は 1 文字単位で自動折り返し。
- 影は `(x + offset_x, y + offset_y)` に先に描き、本体を `(x, y)` に重ねる。

---

## 箇条書き（本文）

定義箇所: `render_image.py` 25〜31 行

| 項目 | デフォルト値 | 設定キー |
|:---|:---|:---|
| フォントサイズ | 48 px | — |
| 行間 | 1.7 ×（行の高さ） | — |
| 開始 X | 90 px | — |
| 開始 Y | 560 px | — |
| 最大テキスト幅 | 900 px | — |
| 文字色 | `#FFFFFF`（白・不透明） | `BULLET_COLOR` |
| 影色 | `#000000A0`（黒・Alpha 160 ≈ 63%） | `BULLET_SHADOW` |
| 影オフセット | `(2, 2)` px | `SHADOW_OFFSET` |

### 入力テキストの解釈

| 形式 | 動作 |
|:---|:---|
| 改行区切り（`\n`） | 各行が 1 項目として描画 |
| `・` 区切り | 改行を含まず `・` がある場合のみ分割（空白項目は除外） |
| 最大幅超過 | 1 文字単位で自動折り返し。継続行は 2 スペースインデント |
| 空行 | 縦スペースのみ挿入（テキスト描画なし） |

---

## テキストシャドウ（共通）

```
描画順:
  1. fill = TITLE_SHADOW（または BULLET_SHADOW）
     位置 = (x + offset_x, y + offset_y)
  2. fill = TITLE_COLOR（または BULLET_COLOR）
     位置 = (x, y)
```

`SHADOW_OFFSET` の指定形式: `x,y`（例: `2,2`）  
単一値（例: `4`）を指定すると X・Y 両方に適用されます。

---

## フォント

| 項目 | 値 |
|:---|:---|
| デフォルトパス | `./assets/fonts/NotoSerifCJKjp-Regular.otf` |
| 設定キー | `FONT_PATH` |
| フォールバック順 | `/usr/share/fonts/…/NotoSerifCJK` → `DejaVuSerif.ttf` → Pillow デフォルト |

タイトルと本文は同一フォントファイルから異なるサイズ（92 px / 48 px）で生成されます。

---

## 動画合成（FFmpeg）

定義箇所: `compose_video.py` 79〜114 行

```
背景動画（mp4）
  └─ scale 1080×1920（短辺フィット → クロップ）
         ↓
       [bg]  ─┐
              ├─ overlay(中央) ─→ 出力 mp4
       [ov]  ─┘
         ↑
オーバーレイ PNG
  └─ scale 1080×1920 以内（長辺フィット・縮小のみ）
```

### フィルタグラフ

```
[0:v] scale=w=1080:h=1920:force_original_aspect_ratio=increase,
      crop=1080:1920, setsar=1 [bg];
[1:v] scale=1080:1920:force_original_aspect_ratio=decrease [ov];
[bg][ov] overlay=(W-w)/2:(H-h)/2 [v]
```

### エンコード設定

| 項目 | 値 |
|:---|:---|
| 映像コーデック | `libx264` |
| CRF | `20` |
| プリセット | `medium` |
| ピクセル形式 | `yuv420p` |
| 音声 | 背景動画トラックをそのまま使用（`0:a?`） |
| 長さ | 最短トラック基準（`-shortest`） |

- 背景動画はファイルパスまたはディレクトリを指定可。ディレクトリ指定時は配下の `.mp4` からランダムに 1 本選択。

---

## エンディング動画連結

定義箇所: `compose_video.py` 125〜203 行

本編 mp4 の末尾に `ending/` 以下の先頭 `.mp4` を連結します。

```
本編.mp4 + ending/xxxxx.mp4
  └─ [0:v][0:a][1:v][1:a] concat=n=2:v=1:a=1 [v][a]
       ─→ tmp_concat.mp4  →  本編.mp4 を上書き
```

| 項目 | 値 |
|:---|:---|
| エンディングディレクトリ | `./ending`（`ENDING_VIDEO` で変更可） |
| 複数ファイル時 | ファイル名昇順で先頭の 1 本を使用 |
| 映像コーデック | `libx264`（CRF=20、`medium`） |
| ピクセル形式 | `yuv420p` |
| ファイルが無い場合 | スキップ（本編はそのまま） |
| ffmpeg 失敗時 | 本編を保持（上書きしない） |

---

## カスタマイズ可能な値の一覧

| 設定キー | CLI オプション | デフォルト |
|:---|:---|:---|
| `TITLE_COLOR` | `--title-color` | `#FFFFFF` |
| `BULLET_COLOR` | `--bullet-color` | `#FFFFFF` |
| `TITLE_SHADOW` | `--title-shadow` | `#000000B4` |
| `BULLET_SHADOW` | `--bullet-shadow` | `#000000A0` |
| `SHADOW_OFFSET` | `--shadow-offset` | `2,2` |
| `FONT_PATH` | `--font` | `./assets/fonts/NotoSerifCJKjp-Regular.otf` |

色は `#RRGGBB` または `#RRGGBBAA`（AA = Alpha）形式で指定します。  
`#RGB` 省略形（3桁）も使用可能です。
