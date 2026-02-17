import random
import time
from pathlib import Path
import xml.etree.ElementTree as ET

import streamlit as st
from streamlit_float import float_init

import streamlit.components.v1 as components
import html
import requests
import json
from groq import Groq
from msg_templates import get_template



# ============================================================
# 0. 定数・CSS（UI）
# ============================================================
CHAT_CSS = """
<style>
    /* Streamlit側のラッパーがはみ出しを切ることがあるので解除 */
    [data-testid="stMarkdownContainer"]{ overflow: visible !important; }
/*    [data-testid="stVerticalBlock"]{ overflow: visible !important; } */

    [data-testid="stMainBlockContainer"]{ padding: 0 16px !important; }

    /* ============================= */
    /* components.html (st.iframe) の余白を潰す */
    /* ============================= */

    /* iframe自体を1pxに固定（Streamlitが150px確保するのを抑える） */
    iframe[title="st.iframe"]{
        height: 1px !important;
        min-height: 1px !important;
        border: 0 !important;
    }

  /* iframeの外側コンテナの余白を消す（Edge/Chrome向け） */
  div.stElementContainer:has(iframe[title="st.iframe"]),
  div.element-container:has(iframe[title="st.iframe"]){
    margin: 0 !important;
    padding: 0 !important;
  }

  /* さらに保険：iframeが入ってるブロックの下余白を詰める */
  div.stVerticalBlock:has(iframe[title="st.iframe"]) > div{
    margin-bottom: 0 !important;
  }

  .titlebar{
    position: sticky;      /* ← fixed じゃなく sticky が安全 */
    top: 0;
    z-index: 9998;         /* ドックより少し下でもOK。上にしたければ99999 */
    background: rgba(255, 140, 0, 0.95); /* オレンジ */
    color: #fff;
    text-align: center;
    font-size: 14px;       /* チャットと同じにしたいならここ */
    line-height: 1.5;
    padding: 15px 0 5px 0;
    border-radius: 0 0 12px 12px;        /* タイトルバー感 */
    margin: 0 0 10px 0;
  }

  /* ページ全体を「1画面」に固定して、bodyスクロールを殺す */
html, body{
  height: 100%;
  overflow: hidden !important;
}

/* Streamlitのメイン領域も高さ成立させる */
[data-testid="stAppViewContainer"],
[data-testid="stApp"],
[data-testid="stMain"]{
  height: 100% !important;
  overflow: hidden !important;
}

/* flex子がスクロールできるようにする定番 */
[data-testid="stVerticalBlock"],
[data-testid="stMainBlockContainer"]{
  min-height: 0 !important;
}

/* chat-wrap に「確実な高さ」を与える（タイトルバー＋ドック分を引く） */
#chatwrap-court, #chatwrap-escort{
    height: calc(100vh - 64px - 110px - 16px) !important;
    overflow-y: auto !important;
    max-height: none !important;

    display: flex;
    flex-direction: column;
    justify-content: flex-end;  /* 常に下寄せ */

}


  /* ============================= */
  /* チャット枠 */
  /* ============================= */
    .chat-wrap{
        max-width: 980px;
        margin: 0 auto;
        padding: 6px 4px;
        max-height: 72vh;
        overflow-y: auto !important;     /* 縦スクロール */
        overflow-x: visible;  /* 横は切らない */
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 12px;
        background: rgba(255,255,255,0.55);
        backdrop-filter: blur(6px);
        scroll-behavior: auto;

        /* 下部固定（次へ）に被らないための余白 */
        padding-bottom: 140px; /* 下部固定ドック分（入力欄も載せるなら） */
    
    }

  .row{
    display:flex;
    gap:12px;
    margin: 10px 0;
    align-items:flex-start;
    position: relative;
    overflow: visible;
  }

  /* 4列の“開始位置アンカー” */
  .cell{
    flex:1;
    min-width:0;
    display:flex;
    flex-direction:column;
    overflow: visible;
  }

  .bubble{
    display:inline-block;
    padding:10px 12px;
    border-radius:16px;
    border:1px solid rgba(0,0,0,0.12);
    box-shadow: 0 1px 0 rgba(0,0,0,0.03);
    font-size:16px;
    line-height:1.5;
    white-space:pre-wrap;

    /* PCではみ出し許容 */
    width: 180%;
    max-width: none;

    overflow: visible;
    position: relative;
    z-index: 2;
  }

  /* speakerごとの微差（薄め） */
  .pros .bubble{background: rgba(255, 99, 99, 0.10); border-width:2px; border-radius:12px;}
  .judge .bubble{background: rgba(255, 210, 90, 0.12); border-radius:18px;}
  .def  .bubble{background: rgba(120, 180, 255, 0.12); border-radius:20px;}
  .player .bubble{background: rgba(180, 180, 180, 0.12); border-style:dashed;}

  /* escortモード：中央1列 */
  .chat-escort .row{ justify-content:center; }
  .chat-escort .escort-cell{
    width: 100%;
    display:flex;
    flex-direction:column;
    align-items:center;
  }
  .chat-escort .bubble{
    width: min(85vw, 520px);
    max-width: 85vw;

  }
  .chat-escort .hint{ text-align:center; }
  .chat-escort .def {align-items:center;}
  .chat-escort .def .bubble {text-align:left;}
  .chat-escort .def .hint {text-align:center;}

  /* 列の中での寄せ（色に頼らず位置で識別） */
  .pros, .judge, .def {align-items:flex-start;}
  .player {align-items:flex-end;}

  .hint{
    color: rgba(0,0,0,0.55);
    font-size: 12px;
    margin-top: 4px;
  }

/* ============================= */
/* ✅ 下部固定ドック（key限定） */
/* ============================= */
.st-key-court_dock,
.st-key-escort_dock{
  padding: 10px 12px;
  border-radius: 999px;
  background: rgba(255,255,255,0.70); /* 半透明 */
  backdrop-filter: blur(6px);
  border: 1px solid rgba(0,0,0,0.08);
  box-shadow: 0 10px 26px rgba(0,0,0,0.14);
  width: min(94vw, 980px);

  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
}

/* ✅ ドック内の primary を「丸アイコン」用に */
.st-key-court_dock div[data-testid="stButton"] > button[kind="primary"],
.st-key-escort_dock div[data-testid="stButton"] > button[kind="primary"]{
  width: 56px !important;
  height: 56px !important;
  border-radius: 999px !important;
  padding: 0 !important;
  display: grid !important;
  place-items: center !important;
  background: rgba(255,255,255,0.92) !important;  /* ← “外丸” を確実に出す */
  border: 1px solid rgba(0,0,0,0.10) !important;
  box-shadow: none !important;
}

/* ドック内のボタン領域を中央寄せにする（Streamlitの分断に耐える） */
.st-key-court_dock div[data-testid="stButton"],
.st-key-escort_dock div[data-testid="stButton"]{
  display: flex !important;
  justify-content: center !important;
}

/* primaryボタンの“中身の赤四角”を殺す（ドック内限定） */
.st-key-court_dock button[kind="primary"] * ,
.st-key-escort_dock button[kind="primary"] *{
  background: transparent !important;
}

/* ✅ アイコン文字（›）を確実に見せる */
.st-key-court_dock button[kind="primary"],
.st-key-escort_dock button[kind="primary"]{
  font-size: 26px !important;
  line-height: 1 !important;
  color: #e33 !important;
}

/* ✅ pill系（なんか言う/言わない/閉廷/外に出る）は丸アイコン化しない */
.st-key-court_dock div[data-testid="stButton"] > button:not([kind="primary"]),
.st-key-escort_dock div[data-testid="stButton"] > button:not([kind="primary"]){
  border-radius: 16px !important;
}

/* dock内の “横並びブロック” を中央寄せに固定 */
.st-key-court_dock div[data-testid="stHorizontalBlock"],
.st-key-escort_dock div[data-testid="stHorizontalBlock"]{
  justify-content: center !important;
  
    display: flex !important;
    flex-direction: row !important;
    gap: 8px !important;
    width: 100% !important;
}

/* ★ stColumn自体も横並びを強制（これが重要） */
.st-key-court_dock div.stColumn,
.st-key-escort_dock div.stColumn{
    flex-direction: row !important;  /* columnをrowに上書き */
    min-width: 0 !important;
}

/* ボタンを100%幅にする */
.st-key-court_dock div.stColumn button,
.st-key-escort_dock div.stColumn button{
    width: 100% !important;
}

/* dock内の stButton ラッパーを中央へ */
.st-key-court_dock div[data-testid="stButton"],
.st-key-escort_dock div[data-testid="stButton"]{
  margin-left: auto !important;
  margin-right: auto !important;
}


  @media (max-width: 520px){
    .chat-wrap{ max-height: 68vh; }
    .row{ gap: 8px; }
    .bubble{ width: 240%; font-size: 15px; }
  }

  /* ============================= */
  /* 📱 スマホ最適化（375px想定） */
  /* ============================= */
  @media (max-width: 420px){
    .chat-wrap:not(.chat-escort) .row{
        display:grid;
        grid-template-columns: 6% 15% 28% 38%;
        gap: 4px;
    }

    .chat-wrap:not(.chat-escort) .cell:nth-child(1){ grid-column:1; }
    .chat-wrap:not(.chat-escort) .cell:nth-child(2){ grid-column:2; }
    .chat-wrap:not(.chat-escort) .cell:nth-child(3){ grid-column:3; }
    .chat-wrap:not(.chat-escort) .cell:nth-child(4){ grid-column:4; }

    /* court（4列）のときだけ bubble を 70vw にする */
    .chat-wrap:not(.chat-escort) .bubble{
        width: 65vw;
        max-width: 85vw;
        font-size: 15px;
        line-height: 1.45;
        word-break: break-word;
        overflow-wrap: anywhere;
    }

    /* 📱 escort は常にflexで中央 */
    .chat-wrap.chat-escort .row{
        display: flex !important;
        justify-content: center !important;
    }
    .chat-wrap.chat-escort .escort-cell{
        align-items: center !important;
        width: 100% !important;
    }
    /* escort（1列）は必ず画面内に収める */
    .chat-wrap.chat-escort .bubble{
        width: 75vw !important;
        max-width: 92vw !important;
        box-sizing: border-box !important;
        margin: 0 auto !important;
    }

    .hint{ font-size:10px; }
    .chat-wrap{ padding: 4px 2px; }

    .st-key-court_dock,
    .st-key-escort_dock{
        width: 92vw !important;
        padding: 8px 10px !important;
    }
    
    /* 送信ボタン（丸アイコン）はサイズ維持 */
    .st-key-court_dock button[kind="primary"],
    .st-key-escort_dock button[kind="primary"]{
        width: 48px !important;
        height: 48px !important;
        font-size: 22px !important;
    }

  }
</style>
"""
# CSS呼び出し関数定義
def inject_global_css():
    st.markdown(CHAT_CSS, unsafe_allow_html=True)


# ============================================================
# 00. 毎回走らせるもの
# ============================================================

# lang属性を日本語に変更するスクリプト
def set_lang_ja():
    # components.html(
    #     """
    #     <script>
    #         try {
    #             window.top.document.documentElement.lang = "ja";
    #         } catch(e) {}
    #     </script>
    #     """,
    #     height=1,

        st.markdown(
        '<meta name="google" content="notranslate">',
        unsafe_allow_html=True
    )

# ============================================================
# 00. セリフ生成（工程1：テンプレート / 工程2：AI）
# ============================================================
# ============================================================
# 00-A. Groq AI呼び出し（工程2）
# ============================================================
# ============================================================
# プロンプト定義（共通）
# ============================================================

PROMPT_BASE = """
【役割】
あなたは軽いユーモアを持つ会話生成エンジンです。
娯楽として生活感や今の天気や時間帯を盛り込んで、法的判断を行わないやり取りを生成します。

【制約】
- 他の人への敬意をもち、穏やかな仕事口調を維持する。語尾は柔らかくする（厳守）
- 同じ内容を繰り返すこと禁止
- 乱暴な言葉・タメ口・怒鳴り・罵倒・命令禁止
- 崩れる時も「投げやり」「照れ」「眠気」など穏やかな範囲で
- 敬語ベースを崩さない（崩れても「……まあ、いいですけど」程度）
- 前回の事案・裁判内容を記憶しない
- 説教禁止・指導禁止・解決提案禁止
- 例文はそのまま読み上げない（禁止）

【コンテキスト情報の使い方】
- 情報はそのまま読み上げない（禁止）
- 体感・間接表現に変換する
- 例：天気「雨」→「傘、重かったですね」
- 例：事案「歯を磨いた」→「些細なことほど、引っかかるんですよね」
"""
PROMPT_CHARACTERS = """
【キャラクター設定】
検察(pros)：
- 基本否定。細部にこだわるが観点がずれる。長引くと飽きる。雑な解決策を出すことがある。
- 気になる観点：行動・場所・状況
- 観点を拾う方向：問題点・違和感・過去発言の矛盾・共通点
- 好きなジャンル：ニュース・乗り物・スポーツ・酒・テレビ
- 崩れ時：投げやり・極論（低頻度）
- 発言は事案について「主張」から始める。問いかけ禁止。「主張」という言葉の使用禁止。
- 構造：主張＋理由 または 主張＋体験談など補足をつける
- 裁判らしい言い回しを使う（「本件」「看過できません」「前例」「結果として」など）
- 良い例：「本件、些細に見えますが、こういった案件を看過すると前例になりかねません。」
- 悪い例：「買い過ぎですね。」「それはダメです。」

弁護(def)：
- 基本肯定。熱意にムラがある。雑。犬を飼っている。好きなジャンルだと話が長い。
- 気になる観点：行動・場所・状況
- 観点を拾う方向：擁護・美化・共感・共通点
- 好きなジャンル：食べ物・音楽・野球・旅・動物
- 崩れ時：調子に乗る・寂しがる・投げやり同調
- 発言は事案の「擁護・肯定」から始める。問いかけ禁止。「養護」という言葉の使用禁止。
- 構造：擁護＋共感 または 擁護＋体験談など補足をつける
- 裁判らしい言い回しを使う（「弁護の立場からは」「情状酌量の余地」「やむを得ない事情」など）
- 良い例：「弁護の立場からは、衝動的ではあっても、やむを得ない事情があったと考えます。」
- 悪い例：「まあ、仕方ないですよ。」「わかりますよ。」

裁判官(judge)：
- 聞いてないようで聞いている
- 関心：場の流れ・時間帯・天気・おやつ在庫・好きなジャンル
- 好きなジャンル：時代劇・映画・イベント・テレビ
- 崩れ時：独り言・テレビ・眠気
- 本気モード：短く鋭い、直後に照れる
"""

PROMPT_OUTPUT_SINGLE = """
【出力ルール】
- セリフ本文のみ出力
- セリフは最大80文字。
- 改行なし・Markdownなし・記号装飾なし
- 役名を含めない・JSON禁止・解説禁止
"""

PROMPT_OUTPUT_BATCH = """
【出力ルール】
- JSON配列のみ出力。説明・コードブロック・改行不要
- 各要素は {"speaker": "pros"|"def"|"judge", "text": "セリフ"}
- セリフは最大80文字。
- 改行なし・Markdownなし・役名を含めない
"""

ROLE_PROMPTS = {
    "pros": """
【状況別補足】
判決理由時：問題点を一言か二言で整理する。長くならない。
お見送り時：少しだけ投げやりな本音が出る。
""",
    "def": """
【状況別補足】
お見送り時：後味が残る一言か二言。プレーヤーの味方。仕事モードをゆるめて少しだけ本音が出る。
おやつコメント時：
- 必ず snack_name のおやつについてコメントする。優しい口調。
- snack_name 以外のおやつ名を言わない
- candidate_names は「他にも候補があった」という文脈でのみ使う
- 例：「今日の雰囲気から、{snack_name}を選んでみました。」
- 例：「{candidate_names}と迷ったんですけど、{snack_name}にしました。」
レアイベント匂わせ時：空気が変わった余韻をふわっと一言。具体的には言わない。
天気コメント時：外の天気と今の時間帯について体感で短く。少し気の利いた感じ。
""",
    "judge": """
【状況別補足】
判決理由時：応酬内容とプレイヤーの発言or沈黙をさりげなく拾う。温かすぎず冷たくもなく。
在庫つぶやき時：おやつの在庫を気にするが在庫数をそのまま言わない。数から連想される内容を独り言のように短く。生活感がある。
""",
}

def _call_groq_api(speaker: str, situation: str, context: dict) -> str | None:
    """
    Groq APIを呼び出してセリフを生成する。
    失敗時は None を返す（呼び出し元でフォールバック）。
    """
    try:
        api_key = st.secrets.get("GROQ_API_KEY", "")
        if not api_key:
            return None

        client = Groq(api_key=api_key)

        # コンテキストをユーザープロンプトに組み立て
        case = context.get("case", "")
        turn_count = context.get("turn_count", 0)
        said = context.get("said", "")
        verdict = context.get("verdict", "")
        weather = context.get("weather_description", "")
        temperature = context.get("temperature", "")
        time_desc = context.get("time_description", "")
        stock_info  = context.get("stock_info", "")
        snack_name = context.get("snack_name", "")

        situation_map = {
            "exchange": "通常の応酬ターン",
            "tired":    "疲れ・関心が逸れている状態",
            "rare_sharp": "珍しく本気で鋭いツッコミ",
            "rare_shy":   "鋭いことを言った直後の照れ隠し",
            "opening":  "裁判の開廷直後の挨拶",
        }
        situation_ja = situation_map.get(situation, situation)

        lines = []
        if case:
            lines.append(f"事案：「{case}」")
        if turn_count:
            lines.append(f"現在{turn_count}ターン目")
        if said:
            lines.append(f"プレイヤーの発言：「{said}」")
        if verdict:
            lines.append(f"判決：{verdict}")
        if weather:
            lines.append(f"今日の天気：{weather}")
        if temperature:
            lines.append(f"気温：{temperature}℃")
        if time_desc:
            lines.append(f"時間帯：{time_desc}")
        if stock_info:
            lines.append(f"おやつ在庫状況：{stock_info}")
        if snack_name:
            lines.append(f"今日のおやつ：{snack_name}")
        lines.append(f"状況：{situation_ja}")
        lines.append("上記の状況で、あなたのセリフを1〜2文で生成してください。")

        user_prompt = "\n".join(lines)

        system_content = (
            PROMPT_BASE
            + PROMPT_CHARACTERS
            + PROMPT_OUTPUT_SINGLE
            + "\n【あなたの役割】\n" + ROLE_PROMPTS.get(speaker, "")
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            # model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=240,
            temperature=0.85,
        )

        text = response.choices[0].message.content.strip()

        # 出力バリデーション
        # 改行は除去して1文にする（弾かずに活かす）
        text = text.replace("\n", " ").strip()

        # Markdown・空文字・異常な長さは弾く
        if not text or text.startswith("#") or text.startswith("```"):
            return None

        # 長すぎる場合もフォールバック（200文字超は異常出力とみなす）
        if len(text) > 200:
            return None

        return text

    except Exception as e:
        return None
    
def _generate_exchange_lines(case: str, target_turns: int, weather: dict, time_description: str = "") -> list[dict] | None:
    """
    応酬ターン分のセリフを1回のAPIコールでまとめて生成する。
    失敗時は None を返す（呼び出し元でフォールバック）。
    """
    try:
        api_key = st.secrets.get("GROQ_API_KEY", "")
        if not api_key:
            return None

        client = Groq(api_key=api_key)

        weather_desc = weather.get("weather_description", "")
        temperature  = weather.get("temperature_2m", "")

        # ターン数に応じてセリフ構成を決める
        # 1ターン = 検察1 + 弁護1、たまに裁判官ノイズ
        # 疲れは後半(80%以降)から出る
        late_start = max(3, int(target_turns * 0.8))

        situation_detail = f"""
        【事案】「{case}」
        【天気】{weather_desc}　【気温】{temperature}℃
        【時間帯】{time_description}
        【応酬ターン数】{target_turns}ターン

        【出力する件数】
        - 基本件数：{target_turns * 2}件（検察{target_turns}件 + 弁護{target_turns}件）
        - 裁判官ノイズ1件を加えた合計{target_turns * 2 + 1}件を出力する
        - 出力件数厳守。
        
        【状況別指示】
        - 1ターン = 検察(pros)1つ + 弁護(def)1つ が基本
        - 裁判官(judge)はjudge_noiseとして1回だけ挟む。2回以上禁止。
        - judge_noiseを挟む位置は全セリフの中間あたり
        - 序盤({late_start}ターン目まで)は通常の応酬のみ
        - 後半({late_start}ターン目以降)は検察か弁護のどちらかが1回だけ疲れた発言をする。2回以上禁止。

        出力例（ターン数2の場合・合計5件）：
        [{{"speaker":"pros","text":"本件、些細に見えますが別の観点からみてみると大きな問題になりかねないと考えます。"}},{{"speaker":"def","text":"弁護の立場からは、やむを得ない事情があったと考えます。うちの犬も似たようなことやりますけど、悪気はないんですよね。"}},{{"speaker":"judge","text":"……ペン、どこ行ったかな。"}},{{"speaker":"pros","text":"この時間帯は疲れがでますね。今日は早めに終わらせたいです。"}},{{"speaker":"def","text":"まあ、そういうのって誰にでもありますよね。私も昨日やりましたし。"}}]        
        """
        prompt = (
            PROMPT_BASE
            + PROMPT_CHARACTERS
            + PROMPT_OUTPUT_BATCH
            + situation_detail
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            # model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "JSONのみ出力してください。説明・コードブロック・改行は不要です。"},
                {"role": "user",   "content": prompt},
            ],

            max_tokens=2000,
            temperature=0.85,
        )

        raw = response.choices[0].message.content.strip()

        # コードブロックが混入した場合の除去
        raw = raw.replace("```json", "").replace("```", "").strip()
        # AIが途中で配列を閉じて再開する不正パターンを修正
        # 例: ],"{ → ,{
        import re
        raw = re.sub(r'\][\s]*,[\s]*"[\s]*\{', ',{', raw)
        raw = re.sub(r'\][\s]*,[\s]*\{', ',{', raw)
        # 末尾が切れている場合の修復
        # 最後の完全な } を探して、そこで閉じる
        last_brace = raw.rfind("}") 
        if last_brace != -1 and not raw.strip().endswith("]"):
            raw = raw[:last_brace + 1] + "]"

        lines = json.loads(raw)

        # バリデーション
        if not isinstance(lines, list):
            return None
        for item in lines:
            if not isinstance(item, dict):
                return None
            if "speaker" not in item or "text" not in item:
                return None
            if item["speaker"] not in ("pros", "def", "judge"):
                return None

        return lines

    except Exception as e:
        return None

def generate_line(speaker: str, situation: str, context: dict | None = None) -> str:
    """
    セリフを生成する。
    - AIを使う場面：exchange / tired / rare_sharp / rare_shy
    - それ以外：テンプレート固定
    - AI失敗 or 上限超過：テンプレートにフォールバック

    Args:
        speaker:   "pros" | "judge" | "def"
        situation: "opening" | "exchange" | "tired" | "noise" | "rare_sharp" | "rare_shy" | "stock" など
        context:   {"case": str, "turn_count": int, "said": str, ...}

    Returns:
        生成されたセリフ文字列
    """
    if context is None:
        context = {}
    
    # ── AIを使わないsituationは即テンプレ ──────────────────
    NO_AI_SITUATIONS = {
        "noise", "opening",
        "escort_snack_cold", "escort_snack_warm", "escort_snack_fresh",
        "ask_taste", "ask_player",
        "verdict_declaration",
    }

    if situation in NO_AI_SITUATIONS:
        return get_template(speaker, situation, **context)
    
    # （工程2ではここで AI を呼ぶ）
    # ── 呼び出し上限チェック ────────────────────────────────
    ai_count = st.session_state.get("ai_call_count", 0)
    ai_max   = st.session_state.get("ai_max_calls", 30)
    if ai_count >= ai_max:
        return get_template(speaker, situation, **context)

    # ── 状況別AI使用確率 ────────────────────────────────────
    turn_count  = st.session_state.get("turn_count", 0)
    target      = st.session_state.get("target_turns", 4)
    is_late     = turn_count >= target * 0.8
    rare_on     = st.session_state.get("rare_event_triggered", False)

    if situation in ("rare_sharp", "rare_shy"):
        ai_prob = 1.0       # レアイベント：必ずAI
    elif situation == "tired" and rare_on:
        ai_prob = 1.0       # 疲れ崩れ直後：必ずAI
    elif is_late:
        ai_prob = 0.8      # 終盤：80%
    else:
        ai_prob = 0.8       # 通常応酬：80%

    # ── AI呼び出し ──────────────────────────────────────────
    if random.random() < ai_prob:
        result = _call_groq_api(speaker, situation, context)
        if result:
            st.session_state.ai_call_count = ai_count + 1
            return result

    # ── フォールバック：テンプレート ────────────────────────
    return get_template(speaker, situation, **context)

def decide_verdict() -> str:
    """
    判決を決定する
    工程1：ランダム
    工程2：この中身をAI補助 + ルールベースに差し替える
    
    Returns:
        "not_guilty" | "lenient" | "guilty"
    """
    # 工程2でここを差し替える
    return random.choice(["not_guilty", "lenient", "guilty"])

# ============================================================
# 00. 天気API（Open-Meteo）
# ============================================================
def fetch_weather() -> dict:
    """
    現在地の天気を取得（Open-Meteo）
    登録不要・完全無料
    失敗時は空dictを返す（フォールバック用）
    """
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=34.69&longitude=135.50"
            "&current=temperature_2m,weathercode"
            "&timezone=Asia%2FTokyo"
        )
        res = requests.get(url, timeout=3)
        data = res.json()
        current = data.get("current", {})

        code = current.get("weathercode")
        if code is not None:
            current["weather_description"] = weather_code_to_description(code)

        # ★ 時間帯を追加
        from datetime import datetime
        now = datetime.now()
        hour = now.hour
        if 5 <= hour < 10:
            time_description = "朝"
        elif 10 <= hour < 12:
            time_description = "午前中"
        elif 12 <= hour < 14:
            time_description = "昼"
        elif 14 <= hour < 17:
            time_description = "午後"
        elif 17 <= hour < 19:
            time_description = "夕方"
        elif 19 <= hour < 22:
            time_description = "夜"
        else:
            time_description = "深夜"
        
        current["time_description"] = time_description
        current["hour"] = hour

        return current
    except Exception:
        return {}
    
def weather_code_to_description(code: int) -> str:
    """
    天気コードを日本語説明に変換
    工程2でAIに渡す context に使う
    """
    if code == 0:
        return "快晴"
    elif code in (1, 2, 3):
        return "曇り"
    elif code in (45, 48):
        return "霧"
    elif code in range(51, 68):
        return "雨"
    elif code in range(71, 78):
        return "雪"
    elif code in range(80, 83):
        return "にわか雨"
    elif code in range(95, 100):
        return "雷雨"
    else:
        return "不明"

def weather_to_comment(weather: dict) -> str:
    """
    天気コードをセリフに変換
    失敗 or 不明 → テンプレートからランダム
    
    Open-Meteoの天気コード（WMO）：
    0        : 快晴
    1, 2, 3  : 晴れ〜曇り
    45, 48   : 霧
    51〜67   : 雨
    71〜77   : 雪
    80〜82   : にわか雨
    95〜99   : 雷雨
    """
    code = weather.get("weathercode")
    temp = weather.get("temperature_2m")

    # 天気取得失敗 → テンプレートにフォールバック
    if code is None:
        return generate_line("def", "escort_greeting", {})

    # 天気コード → セリフ
    if code == 0:
        base = random.choice([
            "いい天気ですね。",
            "……きれいに晴れてますね。",
            "外、明るいですね。",
        ])
    elif code in (1, 2, 3):
        base = random.choice([
            "……曇ってますね。",
            "なんか、どんよりしてますね。",
            "晴れてるんだか曇ってるんだか。",
        ])
    elif code in (45, 48):
        base = random.choice([
            "霧が出てますね。",
            "……靄がかかってますね。",
        ])
    elif code in range(51, 68):
        base = random.choice([
            "雨ですねー。",
            "……降ってますね。",
            "傘、持ってきましたか？",
        ])
    elif code in range(71, 78):
        base = random.choice([
            "……雪ですね。",
            "雪、積もりそうですね。",
        ])
    elif code in range(80, 83):
        base = random.choice([
            "にわか雨ですね。",
            "急に降ってきましたね。",
        ])
    elif code in range(95, 100):
        base = random.choice([
            "……雷、鳴ってますね。",
            "雷雨ですね。早めに帰った方がいいですよ。",
        ])
    else:
        # 不明なコード → テンプレートにフォールバック
        return generate_line("def", "escort_greeting", {})

    # 気温コメントを追加
    if temp is not None:
        if temp <= 3:
            base += " 凍えますね。"
        elif temp <= 10:
            base += " 寒いですね。"
        elif temp >= 35:
            base += " 危険な暑さですね。"
        elif temp >= 28:
            base += " 暑いですね。"

    return base

# ============================================================
# 1. データ（おやつXML）
# ============================================================

@st.cache_data
def load_snacks_xml(filename: str) -> list[dict]:
    """
    XMLを読み込み、辞書のリストで返す。
    snacks.xml: maker/name/temp/fresh/taste
    cheap_snacks.xml: name/taste（＋任意で temp/fresh）
    """
    path = Path(__file__).parent / filename
    if not path.exists():
        return []

    root = ET.parse(path).getroot()
    items = []
    for node in root.findall("snack"):
        d = {}
        for key in ["maker", "name", "temp", "fresh", "taste"]:
            child = node.find(key)
            if child is not None and child.text is not None:
                d[key] = child.text.strip()
        if d.get("name"):
            items.append(d)
    return items

def pick_one(items: list[dict]) -> dict | None:
    return random.choice(items) if items else None

def pick_one_by_taste(items: list[dict], preferred_taste: str | None) -> dict | None:
    """好みに合わせておやつを選ぶ（70%の確率で好みに合わせる）"""
    if not items:
        return None
    
    # 好みが指定されていて、70%の確率で好みに合わせる
    if preferred_taste and random.random() < 0.7:
        matched = [s for s in items if s.get("taste") == preferred_taste]
        if matched:
            return random.choice(matched)
    
    # それ以外はランダム
    return random.choice(items)

def snack_attr_text(s: dict) -> str:
    """表示用（temp/freshが無い場合は出さない）"""
    parts = []
    temp = s.get("temp")
    if temp in ("cold", "normal", "warm"):
        parts.append({"cold": "冷", "normal": "常温", "warm": "温"}[temp])
    fresh = s.get("fresh")
    if fresh in ("true", "false"):
        parts.append("生" if fresh == "true" else "日持ち")
    return " / ".join(parts)

def lawyer_snack_comment(snack: dict, taste_pref: str | None, candidate_names: str = "") -> str:
    """おやつコメント生成"""
    name  = snack.get("name", "")
    temp  = snack.get("temp")
    fresh = snack.get("fresh")
    taste = snack.get("taste")

    context = {
        "snack_name":      name,
        "temp":            temp,
        "fresh":           fresh,
        "taste":           taste,
        "taste_pref":      taste_pref,
        "candidate_names": candidate_names,  # ★ 候補名を追加
    #    "case":            st.session_state.case_text,  # ★ 事案も追加
    }
    
    # 基本コメント
    base = generate_line("def", "escort_snack_comment", context)
    
    # 属性コメント追加
    extras = []
    if temp == "cold":
        extras.append(generate_line("def", "escort_snack_cold", context))
    elif temp == "warm":
        extras.append(generate_line("def", "escort_snack_warm", context))
    
    if fresh == "true":
        extras.append(generate_line("def", "escort_snack_fresh", context))
    
    # ★ 好みコメント（属性で判定）
    if taste_pref == "sweet":
        if taste == "sweet":
            extras.append("甘い方が好きって言ってましたよね。")
        elif taste == "salty":
            extras.append("甘い方が好きって言ってましたよね。…今日はこれしかなくて。")
        elif taste == "neutral":
            extras.append("甘い方が好きって言ってましたよね。…まあ、これも悪くないです。")
    
    elif taste_pref == "salty":
        if taste == "salty":
            extras.append("しょっぱい方が好きって言ってましたよね。")
        elif taste == "sweet":
            extras.append("しょっぱい方が好きって言ってましたよね。…今日はこれしかなくて。")
        elif taste == "neutral":
            extras.append("しょっぱい方が好きって言ってましたよね。…まあ、これも悪くないです。")
    
    return base + (" " + " ".join(extras) if extras else "")

def build_escort_snack_part() -> list[dict]:
    cheap_snacks = load_snacks_xml("cheap_snacks.xml")

    # ★ 簡易版RAG：事案に関連するおやつ上位3件を取得
    candidates = search_snack_by_case(
        case       = st.session_state.case_text,
        taste_pref = st.session_state.taste_pref,
    )

    # 上位3件の中からランダムに1件選ぶ
    snack = random.choice(candidates) if candidates else {
        "maker": "不明",
        "name":  "水",
        "temp":  "normal",
        "fresh": "false",
        "taste": "neutral",
    }

    # ★ 候補リストをコンテキスト用に文字列化
    candidate_names = "、".join([
        c.get("name", "") for c in candidates
        if c.get("name") != snack.get("name")
    ])

    # しょぼおやつ
    bonus = None
    if st.session_state.snack_bonus_flag and random.random() < 0.7:
        bonus = pick_one(cheap_snacks)
    
    # おやつ表示
    script = []
    main_line = f"おやつ：{snack.get('name','')}"
    if snack.get("maker"):
        main_line += f"（{snack.get('maker')}）"
    attrs = snack_attr_text(snack)
    
    script.append({"speaker": "def", "text": main_line})
    if attrs:
        script.append({"speaker": "def", "text": f"（{attrs}）"})
    
    script.append({"speaker": "def", "text": lawyer_snack_comment(snack, st.session_state.taste_pref, candidate_names)})
    
    if bonus is not None:
        script.append({"speaker": "def", "text": f"＋ しょぼおやつ：{bonus.get('name','')}"})
    
    return script

def analyze_snack_stock() -> str:
    """
    snacks.xmlの在庫を分析して、状況テキストを返す（RAG用）
    """
    snacks = load_snacks_xml("snacks.xml")
    if not snacks:
        return "在庫不明"

    total = len(snacks)

    # 温度帯の集計
    temps = {"cold": 0, "normal": 0, "warm": 0}
    for s in snacks:
        t = s.get("temp", "normal")
        if t in temps:
            temps[t] += 1

    # 生ものの集計
    fresh_count = sum(1 for s in snacks if s.get("fresh") == "true")

    # 味の集計
    tastes = {"sweet": 0, "salty": 0, "neutral": 0}
    for s in snacks:
        t = s.get("taste", "neutral")
        if t in tastes:
            tastes[t] += 1

    # 状況テキストを組み立てる
    parts = []
    parts.append(f"在庫総数：{total}件")

    # 偏りチェック
    if tastes["sweet"] > tastes["salty"] * 2:
        parts.append("甘いものが多め")
    elif tastes["salty"] > tastes["sweet"] * 2:
        parts.append("しょっぱいものが多め")
    else:
        parts.append("甘いものとしょっぱいもの、バランスよし")

    # 生もの
    if fresh_count > 0:
        parts.append(f"生もの{fresh_count}件あり（要注意）")

    # 冷たいもの
    if temps["cold"] > 0:
        parts.append(f"冷たいもの{temps['cold']}件あり")

    return "、".join(parts)

def search_snack_by_case(case: str, taste_pref: str | None = None) -> list[dict]:
    """
    簡易版RAG：事案テキストと関連するおやつを上位3件返す
    
    1. おやつ名・メーカーを1つのテキストに結合
    2. 事案テキストと共通する文字を数える
    3. スコアが高い順に返す（同スコアはランダム）
    """
    snacks = load_snacks_xml("snacks.xml")
    if not snacks:
        return []

    case_chars = set(case)  # 事案の文字セット

    scored = []
    for s in snacks:
        # おやつの情報を1つのテキストに結合
        snack_text = " ".join([
            s.get("name",  ""),
            s.get("maker", ""),
            s.get("taste", ""),
            s.get("tags",  ""),  # ★ 追加
        ])
        snack_chars = set(snack_text)

        # 共通文字数をスコアとする
        score = len(case_chars & snack_chars)

        # 好みと一致したらスコア加算
        if taste_pref and s.get("taste") == taste_pref:
            score += 3

        scored.append((score, random.random(), s))

    # スコア降順でソート（同スコアはrandom.random()で順番をシャッフル）
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

    # 上位3件を返す
    return [s for _, _, s in scored[:3]]


# ============================================================
# 2. UI（チャット描画）
# ============================================================

def inject_chat_css():
    """
    CSSは毎回注入する。
    ※StreamlitはrerunのたびDOMが作り直されるため、初回だけだとCSSが消えることがある。
    """
    st.markdown(CHAT_CSS, unsafe_allow_html=True)

def render_chat(messages: list[dict], auto_scroll: bool = True, mode: str = "court"):
    """
    messages: [{"speaker":"pros|judge|def|player", "text":"..."}]
    mode:
      - "court"  : 4列
      - "escort" : 1列（弁護士）
    """
    if not messages:
        return

    # wrap_id は固定にする（DOM探索が安定）
    wrap_id = "chatwrap-escort" if mode == "escort" else "chatwrap-court"

    col_index = {"pros": 0, "judge": 1, "def": 2, "player": 3}
    speaker_label = {"pros": "検察", "judge": "裁判官", "def": "弁護", "player": "あなた"}

    wrap_class = "chat-wrap chat-escort" if mode == "escort" else "chat-wrap"

    parts = [f'<div id="{wrap_id}" class="{wrap_class}">']

    if mode == "escort":
        for m in messages:
            text = html.escape(m.get("text", ""))
            parts.append(
                '<div class="row">'
                '  <div class="escort-cell def">'
                f'    <div class="bubble">{text}</div>'
                '    <div class="hint">弁護士</div>'
                '  </div>'
                '</div>'
            )
    else:
        for m in messages:
            speaker = m.get("speaker", "judge")
            text = html.escape(m.get("text", ""))
            idx = col_index.get(speaker, 1)

            cells = []
            for i in range(4):
                if i == idx:
                    cells.append(
                        f'<div class="cell {speaker}">'
                        f'  <div class="bubble">{text}</div>'
                        f'  <div class="hint">{speaker_label.get(speaker,"")}</div>'
                        f'</div>'
                    )
                else:
                    cells.append('<div class="cell"></div>')
            parts.append('<div class="row">' + "".join(cells) + "</div>")

    bottom_id = f"chatbottom-{mode}-{len(messages)}"
    parts.append(f'<div id="{bottom_id}"></div>')  # ★wrapの中の最下部アンカー
    parts.append("</div>")  # chat-wrap close

    # ★重要：wrap込みのHTMLを1回で出す（入れ子崩れ防止）
    st.markdown("".join(parts), unsafe_allow_html=True)

    nonce = len(messages)  # ← これが毎回変わる

    # 自動スクロール（wrapの中を最下部へ）
    if auto_scroll:

        components.html(
            f"""
            <script>
                const nonce = "{nonce}"; // ← これが入るだけで再実行されやすくなる
                const wrapId = "{wrap_id}";
                const bottomId = "{bottom_id}";
                const doc = (window.parent && window.parent.document) ? window.parent.document : window.top.document;

                function scrollToBottom() {{
                    const wrap = doc.getElementById(wrapId);
                    const bottom = doc.getElementById(bottomId);
                    if (!wrap || !bottom) return;

                    // ①まずwrap内部を最下部へ
                    wrap.scrollTop = wrap.scrollHeight;

                    // ②念のためアンカーを見える位置へ（補助）
                    bottom.scrollIntoView({{ block: "end" }});
                }}

                // まず即時＆遅延
                setTimeout(scrollToBottom, 0);
                setTimeout(scrollToBottom, 80);
                setTimeout(scrollToBottom, 200);
                setTimeout(scrollToBottom, 400);

                // ★高さが変わるまで数回監視（最大1秒）
                let last = -1;
                let tries = 0;
                const timer = setInterval(() => {{
                    const wrap = doc.getElementById(wrapId);
                    if (!wrap) return;

                    const h = wrap.scrollHeight;
                    if (h !== last) {{
                        last = h;
                        scrollToBottom();
                    }}
                    tries += 1;
                    if (tries >= 10) clearInterval(timer);
                }}, 100);
            </script>
            """,
            height=1,
        )

# ============================================================
# 3. state（初期化・リセット・遷移）
# ============================================================

def init_state():
    """session_state 初期化（工程1の箱）"""
    defaults = {
        # 画面
        "scene": "intro",
        "case_text": "",

        # court: phaseマシン
        "phase": "opening",
        "turn_count": 0,
        "target_turns": 0,
        "ask_turn": 0,

        # ask_player
        "player_action": None,  # None|"speak"|"silent"
        "player_text": "",
        "silent_flag": False,
        "ask_by": None,
        "ask_prompt_added": False,

        # 判決
        "verdict": None,

        # イベント枠
        "rare_event_flag": False,
        "rare_event_triggered": False,  # ← 追加（今回のイベントが起きたか）
        "snack_bonus_flag": False,
        "taste_pref": None,
        "taste_asked": False,

        # ログ
        "messages": [],
        "escort_messages": [],

        # escort（次へ式）
        "escort_phase": "start",  # start/showing/done
        "escort_idx": 0,
        "escort_built": False,
        "escort_script": [],
        "escort_taste_asking": False,
        # court（次へ式）
        "court_queue": [],  # 次へで出す待ち行列（まだmessagesに入れない）
        "court_next_phase": None,  # queueを出し切ったら遷移するphase

        # 工程2用（今から準備）
        "ai_call_count": 0,      # この裁判でのAI呼び出し回数
        "ai_max_calls": 30,       # 上限

    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def go(scene_name: str):
    """画面移動（scene変更→rerun）"""
    st.session_state.scene = scene_name
    st.rerun()

def reset_for_new_trial():
    """開廷時：裁判1回分を初期化（case_textは保持）"""
    st.session_state.messages = []
    st.session_state.escort_messages = []
    st.session_state.escort_phase = "start"
    st.session_state.escort_script = []
    st.session_state.escort_idx = 0
    st.session_state.escort_built = False

    st.session_state.phase = "opening"
    st.session_state.turn_count = 0
    st.session_state.target_turns = 4 # random.randint(4, 7)

    # low = max(1, int(st.session_state.target_turns * 0.4))
    # high = max(low, int(st.session_state.target_turns * 0.7))
    # st.session_state.ask_turn = random.randint(low, high)
    st.session_state.ask_turn = st.session_state.target_turns -1

    st.session_state.player_action = None
    st.session_state.player_text = ""
    st.session_state.silent_flag = False
    st.session_state.ask_by = None
    st.session_state.ask_prompt_added = False

    st.session_state.verdict = None
    st.session_state.rare_event_flag = (random.random() < 0.5)
    st.session_state.rare_event_triggered = False
    st.session_state.snack_bonus_flag = False
    st.session_state.taste_pref = None
    st.session_state.taste_asked = False

    # AI呼び出しカウントもリセット
    st.session_state.ai_call_count = 0
    st.session_state.ai_max_calls = 30
    
def reset_for_back_to_intro():
    """最初に戻る：case_textだけ保持し、それ以外はリセット"""
    st.session_state.messages = []
    st.session_state.escort_messages = []
    st.session_state.escort_phase = "start"
    st.session_state.escort_taste_asking = False
    st.session_state.escort_script = []
    st.session_state.escort_idx = 0
    st.session_state.escort_built = False

    st.session_state.phase = "opening"
    st.session_state.turn_count = 0
    st.session_state.target_turns = 0
    st.session_state.ask_turn = 0

    st.session_state.player_action = None
    st.session_state.player_text = ""
    st.session_state.silent_flag = False
    st.session_state.ask_by = None
    st.session_state.ask_prompt_added = False

    st.session_state.verdict = None
    st.session_state.rare_event_flag = False
    st.session_state.snack_bonus_flag = False
    st.session_state.taste_pref = None
    st.session_state.taste_asked = False

    st.session_state.ai_call_count = 0

def dock_area(key: str):
    dock = st.container(key=key)
    dock.float(
        "position: fixed;"
        "left: 50%;"
        "bottom: 14px;"
        "transform: translateX(-50%);"
        "z-index: 999999;"
        "width: min(94vw, 980px);"   # ★fit-contentをやめる
    )
    return dock


# タイトルバー
def render_titlebar(text: str):
    st.markdown(f"""
    <div class="titlebar">{text}</div>
    """, unsafe_allow_html=True)


# ============================================================
# 4. ロジック：escort 台本生成（startを薄くする）
# ============================================================
def build_escort_script() -> list[dict]:
    """お見送り（弁護士＋おやつ）を台本にして返す"""
    v = st.session_state.verdict
    silent = st.session_state.silent_flag

    # ★ 最初にリセット
    st.session_state.escort_taste_asking = False
    
    # 天気コメント（API取得）
    weather = fetch_weather()
    # コンテキスト準備
    context = {
        "verdict":             v,
        "silent":              silent,
        "said":         st.session_state.player_text if not silent else None,
        "case":                st.session_state.case_text,
        "weather_description": weather.get("weather_description", ""),
        "temperature":         weather.get("temperature_2m", ""),
    }
    # 天気コメント（フォールバック）
    greeting = weather_to_comment(weather)
    
    script = [{"speaker": "def", "text": greeting}]
    
    # 判決に応じたメッセージ（2件目）
    if v == "not_guilty":
        situation = "escort_not_guilty_silent" if silent else "escort_not_guilty_spoke"
    elif v == "lenient":
        situation = "escort_lenient_silent" if silent else "escort_lenient_spoke"
    else:
        situation = "escort_guilty_silent" if silent else "escort_guilty_spoke"
    
    msg = generate_line("def", situation, context)
    script.append({"speaker": "def", "text": msg})
    
    # レアイベントが起きていたら匂わせる
    if st.session_state.rare_event_triggered:
        rare_comment = generate_line("def", "escort_rare_event", context)
        script.append({"speaker": "def", "text": rare_comment})

    # ★ 質問がない場合は、おやつも一緒に返す
    if st.session_state.taste_asked or random.random() >= 0.7:
        script.extend(build_escort_snack_part())
    else:
        # 質問する場合は、フラグだけ立てる（質問文はまだ追加しない）
        st.session_state.escort_taste_asking = True
    
    return script

# ============================================================
# 5. 画面：intro / court / escort / end
# ============================================================

init_state()
float_init()

#CSS設定
inject_global_css()
#日本語化
set_lang_ja()

# ------------------------------------------------------------
# ① intro
# ------------------------------------------------------------
if st.session_state.scene == "intro":
    render_titlebar("ゆるゆる裁判所")

    # ── AI利用案内（工程2セーフティ表示） ──────────────────
    st.caption("⚠️ 生成AIを利用しています。個人情報は入力しないでください。")
    st.write("何でもとりあえず裁いてしまう裁判所です。\n今日は、どんなことがありましたか。")

    case_text = st.text_input(
        "事案",
        value=st.session_state.case_text,
        max_chars=50,
        placeholder="あったかい黒豆茶を飲んだ / コープで玉ねぎ買ってきた など",
        label_visibility="collapsed",
    )
    st.session_state.case_text = case_text

    can_start = len(case_text.strip()) >= 1
    if st.button("開廷", disabled=not can_start):
        reset_for_new_trial()
        go("court")

# ------------------------------------------------------------
# ② court
# ------------------------------------------------------------
elif st.session_state.scene == "court":
    
    render_titlebar("裁判中")

    # ─────────────────────────────────────────
    # 0) まず phase 更新（queueを出し切った直後の遷移）
    # ─────────────────────────────────────────
    if (
        st.session_state.court_next_phase is not None
        and len(st.session_state.court_queue) == 0
    ):
        st.session_state.phase = st.session_state.court_next_phase
        st.session_state.court_next_phase = None

    # ─────────────────────────────────────────
    # 1) 次に出すセリフを queue に積む

    if len(st.session_state.court_queue) == 0:
        phase = st.session_state.phase

        if phase == "opening":
            case    = st.session_state.case_text.strip()
            weather = fetch_weather()
            context = {
                "case":                case,
                "weather_description": weather.get("weather_description", ""),
                "temperature":         weather.get("temperature_2m", ""),
            }

            # openingはテンプレ固定
            st.session_state.court_queue.extend([
                {"speaker": "judge", "text": get_template("judge", "opening", case=case)},
                {"speaker": "pros",  "text": get_template("pros",  "opening")},
                {"speaker": "def",   "text": get_template("def",   "opening")},
            ])

            # exchange分を1回のAPIコールでまとめて生成してキューに積む
            exchange_lines = _generate_exchange_lines(
                case         = case,
                target_turns = st.session_state.target_turns,
                weather      = weather,
                time_description = weather.get("time_description", ""),
            )

            if exchange_lines:
                # AI生成成功：全部キューに積む
                st.session_state.court_queue.extend(exchange_lines)
                st.session_state.ai_call_count += 1
                # ターンカウントをtarget_turnsまで一気に進める
                st.session_state.turn_count = st.session_state.target_turns
            else:
                # AI失敗：フォールバック（従来通り1ターンずつ生成）
                st.session_state.turn_count = 0

            st.session_state.court_next_phase = "exchange"

        elif phase == "exchange":
            # まとめて生成済みの場合
            if st.session_state.turn_count >= st.session_state.target_turns:
                # ask_turnが設定されている場合はask_playerを挟む
                if st.session_state.ask_turn <= st.session_state.target_turns:
                    st.session_state.court_next_phase = "ask_player"
                else:
                    st.session_state.court_next_phase = "verdict_prep"
            else:
                context = {
                    "case": st.session_state.case_text,
                    "turn_count": st.session_state.turn_count,
                }
                
                # ターンが進んできたら「疲れ」が出やすくする（後半20%）
                # ターンが2以上になってから疲れが出るようにする
                is_early_game = st.session_state.turn_count < 2
                is_late_game  = st.session_state.turn_count >= st.session_state.target_turns * 0.8
                tired_chance  = 0.0 if is_early_game else (0.3 if is_late_game else 0.1)
                
                # 検察の発言（疲れる可能性）
                pros_situation = "tired" if random.random() < tired_chance else "exchange"
                pros_text = generate_line("pros", pros_situation, context)
                st.session_state.court_queue.append({
                    "speaker": "pros",
                    "text": pros_text
                })
                
                # ★ レアイベント発火判定（疲れた直後に25%）
                if (pros_situation == "tired" 
                    and st.session_state.rare_event_flag 
                    and not st.session_state.rare_event_triggered):
                    
                    if random.random() < 0.25:
                        # レアイベント発生！
                        st.session_state.rare_event_triggered = True
                        st.session_state.snack_bonus_flag = True
                        
                        # 誰がツッコむか（弁護 or 裁判官）
                        reactor = random.choice(["def", "judge"])
                        
                        # 鋭い一言
                        st.session_state.court_queue.append({
                            "speaker": reactor,
                            "text": generate_line(reactor, "rare_sharp", context)
                        })
                        
                        # 照れて逃げる
                        st.session_state.court_queue.append({
                            "speaker": reactor,
                            "text": generate_line(reactor, "rare_shy", context)
                        })
                
                # 裁判官のノイズ（20%、レアイベントが起きてない時だけ）
                if random.random() < 0.2 and not st.session_state.rare_event_triggered:
                    st.session_state.court_queue.append({
                        "speaker": "judge",
                        "text": generate_line("judge", "noise", context)
                    })
                
                # 弁護の発言（疲れる可能性）
                def_situation = "tired" if random.random() < tired_chance else "exchange"
                def_text = generate_line("def", def_situation, context)
                st.session_state.court_queue.append({
                    "speaker": "def",
                    "text": def_text
                })
                
                # ★ 弁護が疲れた直後にもレアイベント判定
                if (def_situation == "tired" 
                    and st.session_state.rare_event_flag 
                    and not st.session_state.rare_event_triggered):
                    
                    if random.random() < 0.25:
                        st.session_state.rare_event_triggered = True
                        st.session_state.snack_bonus_flag = True
                        
                        reactor = random.choice(["pros", "judge"])
                        
                        st.session_state.court_queue.append({
                            "speaker": reactor,
                            "text": generate_line(reactor, "rare_sharp", context)
                        })
                        
                        st.session_state.court_queue.append({
                            "speaker": reactor,
                            "text": generate_line(reactor, "rare_shy", context)
                        })

                # ターン数は「ターンを積んだ時点」で増やす（表示は後追い）
                st.session_state.turn_count += 1

                if st.session_state.turn_count == st.session_state.ask_turn:
                    st.session_state.court_next_phase = "ask_player"
                elif st.session_state.turn_count >= st.session_state.target_turns:
                    st.session_state.court_next_phase = "verdict_prep"
                else:
                    st.session_state.court_next_phase = "exchange"

        # ★ 新しいphase
        elif phase == "ask_taste":
            # ここでは何も積まない（ユーザー選択を待つ）
            pass
        

        elif phase == "verdict_prep":

            # 在庫つぶやき（25%）
            if random.random() < 0.25:

                # ★ RAG：在庫を分析してcontextに渡す
                stock_info = analyze_snack_stock()
                st.session_state.court_queue.append({
                    "speaker": "judge",
                    "text":    generate_line("judge", "stock", {
                        "stock_info": stock_info
                    }),
                })
                
            # ★ 甘い/しょっぱい質問（70%、まだ聞いてない場合）
            if not st.session_state.taste_asked and random.random() < 0.3:
                st.session_state.court_queue.append({
                    "speaker": "def",
                    "text": generate_line("def", "ask_taste", {})
                })
                st.session_state.taste_asked = True
                st.session_state.court_next_phase = "ask_taste"  # ← 新しいphase
            else:
                st.session_state.court_next_phase = "verdict"

        elif phase == "verdict":

            if st.session_state.verdict is None:
                st.session_state.verdict = decide_verdict()
            
            # コンテキスト準備
            context = {}
            
            # 理由づけ
            if st.session_state.silent_flag:
                reason = generate_line("judge", "verdict_reason_silent", context)
            else:
                said = st.session_state.player_text.strip()
                context["said"] = said
                reason = generate_line("judge", "verdict_reason_spoke", context)
            
            st.session_state.court_queue.append({"speaker": "judge", "text": reason})
            
            # 判決宣告
            v = st.session_state.verdict
            v_label = {"not_guilty": "無罪", "lenient": "情状酌量", "guilty": "有罪"}[v]
            context["verdict_label"] = v_label
            
            declaration = generate_line("judge", "verdict_declaration", context)
            st.session_state.court_queue.append({"speaker": "judge", "text": declaration})
            
            st.session_state.court_next_phase = "done"

    # ─────────────────────────────────────────
    # 2) 表示（いま確定している messages だけ）
    # ─────────────────────────────────────────
    render_chat(st.session_state.messages, auto_scroll=True, mode="court")

    # ─────────────────────────────────────────
    # 3) 操作UI（下部固定ドック）
    #    - ask_player: なんか言う / 言わない（＋入力）
    #    - done: 閉廷
    #    - それ以外: 次へ
    # ─────────────────────────────────────────
    dock = st.container(key="court_dock")

    with dock:
        # phaseで中身を切り替える
        if st.session_state.phase == "ask_player":

            # 促す人の決定
            if st.session_state.ask_by is None:
                r = random.random()
                st.session_state.ask_by = "judge" if r < 0.7 else ("def" if r < 0.9 else "pros")

            # 促し台詞を1回だけ messages に積む（※見せる）
            if not st.session_state.ask_prompt_added:

                prompt = generate_line(st.session_state.ask_by, "ask_player", {})
                st.session_state.messages.append({"speaker": st.session_state.ask_by, "text": prompt})
                st.session_state.ask_prompt_added = True
                st.rerun()

            if st.session_state.player_action != "speak":
                c1, c2 = st.columns(2, gap="small")
                with c1:
                    if st.button("なんか言う", use_container_width=True, key="court_speak"):
                        st.session_state.player_action = "speak"
                        st.rerun()
                with c2:
                    if st.button("言わない", use_container_width=True, key="court_silent"):
                        st.session_state.player_action = "silent"
                        st.session_state.silent_flag = True
                        st.session_state.player_text = ""
                        st.session_state.messages.append({"speaker": "player", "text": "・・・・・・"})
                        st.session_state.phase = "verdict_prep"
                        st.rerun()

            else:
                # ✅ 横並び：入力（広）＋ 送信（丸アイコン）
                c1, c2 = st.columns([6, 1], gap="small")
                with c1:
                    player_text = st.text_input(
                        "",
                        value=st.session_state.player_text,
                        max_chars=50,
                        placeholder="例：いや、これは事故で… など",
                        label_visibility="collapsed",
                    )
                    st.session_state.player_text = player_text
                with c2:
                    send = st.button("›", type="primary", use_container_width=True, key="court_send")

                if send:
                    txt = st.session_state.player_text.strip()
                    if len(txt) == 0:
                        st.warning("空白だけは送れません。")
                    else:
                        st.session_state.silent_flag = False
                        st.session_state.messages.append({"speaker": "player", "text": txt})
                        st.session_state.phase = "verdict_prep"
                        st.rerun()

        # ★ 新しいphase
        elif st.session_state.phase == "ask_taste":
            # 甘い / しょっぱい の2択
            c1, c2 = st.columns(2, gap="small")
            with c1:
                if st.button("甘い", use_container_width=True, key="taste_sweet"):
                    st.session_state.taste_pref = "sweet"
                    st.session_state.messages.append({"speaker": "player", "text": "（甘いほうにした）"})
                    st.session_state.phase = "verdict"
                    st.rerun()
            with c2:
                if st.button("しょっぱい", use_container_width=True, key="taste_salty"):
                    st.session_state.taste_pref = "salty"
                    st.session_state.messages.append({"speaker": "player", "text": "（しょっぱいほうにした）"})
                    st.session_state.phase = "verdict"
                    st.rerun()

        elif st.session_state.phase == "done":
            if st.button("閉廷", use_container_width=True):
                go("escort")

        else:
            if st.button("›", key="court_next", type="primary"):
                if st.session_state.court_queue:
                    st.session_state.messages.append(st.session_state.court_queue.pop(0))
                st.rerun()

    # ここで“dock全体”を固定
    dock.float(
        "position: fixed;"
        "left: 50%;"
        "bottom: 14px;"
        "transform: translateX(-50%);"
        "z-index: 9999;"
        "width: min(94vw, 980px);"
    )

# ------------------------------------------------------------
# ③ escort
# ------------------------------------------------------------
elif st.session_state.scene == "escort":
    
    render_titlebar("お見送り")

    if st.session_state.escort_phase == "start":
        st.session_state.escort_script = build_escort_script()

        # ★idx=0 で「1件目」を出す
        st.session_state.escort_idx = 0

        st.session_state.escort_phase = "showing"
        st.rerun()

    if st.session_state.escort_phase == "showing":
        script = st.session_state.escort_script
        idx = st.session_state.escort_idx

        # idx=0 で 1件目が見える
        visible = script[: idx + 1]
        render_chat(visible, auto_scroll=True, mode="escort")

        st.divider()

        # 次がまだあるなら「次へ」→ ドックに入れる
        if idx < len(script) -1 :
            dock = dock_area("escort_dock")
            with dock:
                # “次へ” は丸アイコン運用（primary）
                if st.button("›", key="escort_next", type="primary", use_container_width=True):
                    st.session_state.escort_idx += 1
                    st.rerun()

        # ★ 全部出し切った後に、質問があるかチェック
        elif st.session_state.escort_taste_asking:
            dock = dock_area("escort_dock")
            with dock:
                if st.button("›", key="escort_next", type="primary", use_container_width=True):

                    # 質問文を追加
                    st.session_state.escort_script.append({
                        "speaker": "def",
                        "text": generate_line("def", "ask_taste", {})
                    })
                    st.session_state.taste_asked = True
                    st.session_state.escort_phase = "asking_taste"
                    st.rerun()
        
        else:
            # 質問もなく、全部出し切った
            st.session_state.escort_phase = "done"
            st.rerun()

    if st.session_state.escort_phase == "asking_taste":
        # 質問までを表示
        render_chat(st.session_state.escort_script, auto_scroll=True, mode="escort")
        
        # ドックに選択ボタン
        dock = dock_area("escort_dock")
        with dock:
            c1, c2 = st.columns(2, gap="small")
            with c1:
                if st.button("甘い", use_container_width=True, key="escort_taste_sweet"):
                    st.session_state.taste_pref = "sweet"
                    st.session_state.escort_taste_asking = False
                    # おやつを追加する前の長さを記録
                    before_len = len(st.session_state.escort_script)
                    # おやつ処理を追加
                    st.session_state.escort_script.extend(build_escort_snack_part())
                    # ★ おやつの1件目（before_len の位置）から表示開始
                    st.session_state.escort_idx = before_len

                    st.session_state.escort_phase = "showing"
                    st.rerun()
            with c2:
                if st.button("しょっぱい", use_container_width=True, key="escort_taste_salty"):
                    st.session_state.taste_pref = "salty"
                    st.session_state.escort_taste_asking = False
                    # おやつを追加する前の長さを記録
                    before_len = len(st.session_state.escort_script)
                    # おやつ処理を追加
                    st.session_state.escort_script.extend(build_escort_snack_part())
                    # ★ おやつの1件目（before_len の位置）から表示開始
                    st.session_state.escort_idx = before_len

                    st.session_state.escort_phase = "showing"                  
                    st.rerun()

    if st.session_state.escort_phase == "done":
        render_chat(st.session_state.escort_script, auto_scroll=True, mode="escort")

        dock = dock_area("escort_dock")
        with dock:
            # “外に出る” はピル運用にしたいなら primary を外す（おすすめ）
            if st.button("外に出る", use_container_width=True, key="escort_out"):
                go("end")

# ------------------------------------------------------------
# ④ end
# ------------------------------------------------------------
elif st.session_state.scene == "end":

    render_titlebar("では、また。")

    st.write("同じ事案でも、別の展開になるかもしれません。")

    if st.button("最初に戻る"):
        reset_for_back_to_intro()
        go("intro")
