# CLAUDE.md — ゆるゆる裁判所

## プロジェクト概要

事案を入力すると、検察・弁護士・裁判官の3キャラクターがゆるく裁判を繰り広げ、最終的に判決を下すゲームアプリ。
お見送りでは弁護士が事案にベクトル検索で選んだおやつを渡してくれる。

- **フレームワーク**: Streamlit + streamlit-float
- **AI**: Groq API（llama-3.3-70b-versatile）
- **ベクトル検索**: ChromaDB + sentence-transformers（paraphrase-multilingual-MiniLM-L12-v2）
- **天気API**: Open-Meteo（登録不要・無料）
- **Python**: 3.11（chromadb互換性のため）
- **デプロイ**: Streamlit Community Cloud

---

## ファイル構成

```
yuruyuru_court/
├── app.py                  # メインアプリ（単一ファイル、約2000行）
├── msg_templates.py        # テンプレートセリフ集
├── snacks.xml              # おやつデータ（RAG用 desc 付き）
├── cheap_snacks.xml        # しょぼおやつデータ（レアイベント用）
├── requirements.txt
├── .streamlit/
│   ├── secrets.toml        # GROQ_API_KEY（Git管理外）
│   └── config.toml
└── assets/
    └── rooftop_bg_ultralight_1600x900.jpg
```

---

## app.py の構成（セクション番号）

| セクション | 内容 |
|-----------|------|
| `# 0.` | 定数・CSS（CHAT_CSS / inject_global_css） |
| `# 00.` | 毎回走らせる処理（言語設定など） |
| `# 00-A.` | Groq AI呼び出し（`_call_groq_api` / `_generate_exchange_lines`） |
| `# 00.` | セリフ生成エントリ（`generate_line` / `decide_verdict`） |
| `# 00.` | 天気API（`fetch_weather` / `weather_to_comment`） |
| `# 1.` | おやつXML読み込み（`load_snacks_xml` / `lawyer_snack_comment` など） |
| `# 2.` | おやつRAG（ChromaDB / `build_chroma_collection` / `query_snack_by_case`） |
| `# 3.` | UIパーツ（チャットバブル生成 HTML / タイトルバー） |
| `# 4.` | シーン：intro（事案入力） |
| `# 5.` | シーン：court（裁判進行） |
| `# 6.` | シーン：escort（お見送り） |
| `# 7.` | シーン：end（終了） |
| `# main` | シーン振り分け（`st.session_state.scene` で分岐） |

---

## シーン遷移

```
intro → court → escort → end → intro（リセット）
```

`st.session_state.scene` の値で現在のシーンを管理。

---

## セリフ生成の仕組み（2段階方式）

1. **工程1（テンプレート）**: `msg_templates.py` の `get_template()` から固定セリフをランダム選択
2. **工程2（AI）**: Groq API で動的生成（失敗時はテンプレートにフォールバック）

| situation | AI使用 | 備考 |
|-----------|--------|------|
| `exchange` | ✅（80%） | 通常の応酬 |
| `tired` | ✅（80%〜100%） | 後半の疲れ発言 |
| `rare_sharp` / `rare_shy` | ✅（100%） | レアイベント |
| `opening` / `noise` / `ask_player` など | ❌ | テンプレート固定 |

- 1裁判あたりAI呼び出し上限：**30回**（`ai_call_count` / `ai_max_calls`）
- 応酬は1回のAPIコールで複数ターン分を一括生成（`_generate_exchange_lines`）

### AIプロンプト構成

```
PROMPT_BASE（共通ルール）
+ PROMPT_CHARACTERS（3キャラクター設定）
+ PROMPT_OUTPUT_SINGLE または PROMPT_OUTPUT_BATCH（出力形式）
+ ROLE_PROMPTS[speaker]（キャラクター別補足）
```

---

## おやつRAG

- `snacks.xml` の各おやつは `<desc>` フィールドに「どんな場面で選ばれるか」の情景文を持つ
- ChromaDB にベクトル化して格納（`build_chroma_collection`）
- 事案テキストに意味的に近いおやつ上位3件を取得し、ランダムに1つ選択（`query_snack_by_case`）
- 弁護士が「なぜこれを選んだか」をAIが `desc` をヒントに生成して話す
- 裁判官の在庫つぶやきにも `desc` を利用

---

## キャラクター設定

| キャラ | ID | 特徴 |
|--------|-----|------|
| 検察 | `pros` | 基本否定。押されると弱気。「本件」「看過できません」など裁判語 |
| 弁護士 | `def` | 基本肯定。熱意にムラ。犬を飼っている。好きなジャンルで話が長い |
| 裁判官 | `judge` | 聞いてないようで聞いている。おやつ・テレビが気になる |

---

## レアイベント

一定確率で発生。`st.session_state.rare_event_triggered` フラグで管理。
- `rare_sharp`：キャラが珍しく本気で鋭いツッコミ（AI必須）
- `rare_shy`：鋭いことを言った直後の照れ隠し（AI必須）

---

## UI 構成

- **チャット**: 4列グリッド（検察 / 裁判官 / 弁護士 / プレイヤー）、HTMLバブルで描画
- **下部固定ドック**: `streamlit-float` で `court_dock` / `escort_dock` を固定
- **背景**: `assets/rooftop_bg_ultralight_1600x900.jpg` をbase64化してCSSに埋め込み
- **CSS**: `CHAT_CSS` 定数として `app.py` 冒頭に埋め込み（約430行）
- **スマホ対応**: `@media (max-width: 420px)` でグリッドレイアウトに切り替え

---

## セッションステート 主要キー

| キー | 型 | 説明 |
|------|----|------|
| `scene` | str | 現在のシーン（`intro` / `court` / `escort` / `end`） |
| `case_text` | str | プレイヤーが入力した事案 |
| `chat_queue` | list | 表示待ちのセリフキュー |
| `turn_count` | int | 現在の応酬ターン数 |
| `target_turns` | int | 今回の目標ターン数 |
| `verdict` | str | 判決（`not_guilty` / `lenient` / `guilty`） |
| `ai_call_count` | int | AI呼び出し回数（上限管理） |
| `ai_max_calls` | int | AI呼び出し上限（デフォルト30） |
| `rare_event_triggered` | bool | レアイベント発生フラグ |
| `player_said` | str | プレイヤーの発言内容 |
| `preferred_taste` | str | プレイヤーの味の好み（`sweet`/`salty`） |
| `weather` | dict | 天気データ（Open-Meteo） |

---

## 環境構築

```bash
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**APIキー設定**（`.streamlit/secrets.toml`）:
```toml
GROQ_API_KEY = "your_groq_api_key"
```

**起動**:
```bash
streamlit run app.py
```

---

## 今後の検討事項（README.mdより）

- [ ] キャラクターの「経験DB」をベクトル化して「そういえば」発言を増やす
- [ ] おやつデータの追加・カスタマイズUI
- [ ] 判決のAI補助（現在は `decide_verdict()` がランダム返却）
