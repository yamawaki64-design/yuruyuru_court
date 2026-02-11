import random
import time
from pathlib import Path
import xml.etree.ElementTree as ET

import streamlit as st
from streamlit_float import float_init

import streamlit.components.v1 as components
import html
from msg_templates import get_template

# ============================================================
# 00. セリフ生成（工程1：テンプレート / 工程2：AI）
# ============================================================

def generate_line(speaker: str, situation: str, context: dict | None = None) -> str:
    """
    セリフを生成する（工程1はテンプレート、工程2でAI化）
    
    Args:
        speaker: "pros" | "judge" | "def"
        situation: "opening" | "exchange" | "tired" | "noise" | "rare_sharp" | "rare_shy" | "stock"
        context: {
            "case_text": str,
            "turn_count": int,
            "messages": list,
            "player_text": str | None,
            ...
        }
    
    Returns:
        生成されたセリフ
    """
    if context is None:
        context = {}
    
    # 工程1：テンプレートから選ぶ
    # 工程2：ここを AI呼び出しに差し替える
    
    # AI呼び出し回数チェック（工程2用の準備）
    if "ai_call_count" in st.session_state and st.session_state.ai_call_count >= st.session_state.get("ai_max_calls", 8):
        # 上限超過：テンプレートにフォールバック
        return get_template(speaker, situation, **context)
    
    # 工程1：すべてテンプレート
    # （工程2ではここで AI を呼ぶ）
    line = get_template(speaker, situation, **context)
    
    # カウント増加（工程2用の準備）
    if "ai_call_count" in st.session_state and situation in ["exchange", "rare_sharp"]:
        st.session_state.ai_call_count += 1
    
    return line

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

# ============================================================
# 00. 毎回走らせるもの
# ============================================================

# lang属性を日本語に変更するスクリプト
def set_lang_ja():
    components.html(
        """
        <script>
          try {
            window.top.document.documentElement.lang = "ja";
          } catch(e) {}
        </script>
        """,
        height=1,
    )

set_lang_ja()

def inject_global_css():
    st.markdown(CHAT_CSS, unsafe_allow_html=True)

inject_global_css()



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



def lawyer_snack_comment(snack: dict, taste_pref: str | None) -> str:
    """おやつコメント生成"""
    name = snack.get("name", "")
    temp = snack.get("temp")
    fresh = snack.get("fresh")
    taste = snack.get("taste")  # ← 追加

    context = {
        "snack_name": name,
        "temp": temp,
        "fresh": fresh,
        "taste": taste,
        "taste_pref": taste_pref,
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
    """おやつ部分だけを生成"""
    snacks = load_snacks_xml("snacks.xml")
    cheap_snacks = load_snacks_xml("cheap_snacks.xml")
    
    # 好みに合わせて選ぶ
    snack = pick_one_by_taste(snacks, st.session_state.taste_pref) or {
        "maker": "不明",
        "name": "水",
        "temp": "normal",
        "fresh": "false",
        "taste": "neutral"
    }
    
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
    script.append({"speaker": "def", "text": lawyer_snack_comment(snack, st.session_state.taste_pref)})
    
    if bonus is not None:
        script.append({"speaker": "def", "text": f"＋ しょぼおやつ：{bonus.get('name','')}"})
    
    return script

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

    parts = []
    parts.append(f'<div id="{wrap_id}" class="{wrap_class}">')

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
        "ai_max_calls": 8,       # 上限

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
    st.session_state.target_turns = random.randint(4, 8)

    low = max(1, int(st.session_state.target_turns * 0.4))
    high = max(low, int(st.session_state.target_turns * 0.7))
    st.session_state.ask_turn = random.randint(low, high)

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
    
    # コンテキスト準備
    context = {
        "verdict": v,
        "silent": silent,
        "player_text": st.session_state.player_text if not silent else None,
    }
    
    # situation を決める（判決 × 発言有無）
    if v == "not_guilty":
        situation = "escort_not_guilty_silent" if silent else "escort_not_guilty_spoke"
    elif v == "lenient":
        situation = "escort_lenient_silent" if silent else "escort_lenient_spoke"
    else:  # guilty
        situation = "escort_guilty_silent" if silent else "escort_guilty_spoke"
    
    # 弁護士の一言を生成
    msg = generate_line("def", situation, context)
    
    script = [{"speaker": "def", "text": msg}]
    
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

# ------------------------------------------------------------
# ① intro
# ------------------------------------------------------------
if st.session_state.scene == "intro":
    render_titlebar("ゆるゆる裁判所")
    st.write("何でもとりあえず裁いてしまう裁判所です。\n今日は、どんなことがありましたか。")

    case_text = st.text_input(
        "事案",
        value=st.session_state.case_text,
        max_chars=50,
        placeholder="歯を磨いた / コーヒーをこぼした / エレベーターがギュウギュウだった",
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
    if st.session_state.court_next_phase is not None and len(st.session_state.court_queue) == 0:
        st.session_state.phase = st.session_state.court_next_phase
        st.session_state.court_next_phase = None

    # ─────────────────────────────────────────
    # 1) 次に出すセリフを queue に積む（まだmessagesへは入れない）
    #    ※queueが空のときだけ積むのがコツ
    # ─────────────────────────────────────────
    pros_lines = [
        "検察としては、ここを見逃すと秩序が崩れます。",
        "小さいことほど、積み重なると大きいです。",
        "本件、軽く見せかけて地味にダメージがあります。",
    ]
    def_lines = [
        "弁護の立場からは、そこまでのことではないと考えます。",
        "状況を聞くと、やむを得ない面もあります。",
        "それは“やった”というより“起きた”に近いかもしれません。",
    ]
    judge_noise = [
        "（裁判官、ペンを回している）",
        "……寒いですね、今日。",
        "（裁判官、書類の角を揃えている）",
    ]

    if len(st.session_state.court_queue) == 0:
        phase = st.session_state.phase

        if phase == "opening":
            case = st.session_state.case_text.strip()

            context = {"case": case}
            
            st.session_state.court_queue.extend([
                {"speaker": "judge", "text": generate_line("judge", "opening", context)},
                {"speaker": "pros",  "text": generate_line("pros", "opening", context)},
                {"speaker": "def",   "text": generate_line("def", "opening", context)},
            ])

            st.session_state.court_next_phase = "exchange"

        elif phase == "exchange":

            context = {
                "case": st.session_state.case_text,
                "turn_count": st.session_state.turn_count,
            }
            
            # ターンが進んできたら「疲れ」が出やすくする（後半30%）
            is_late_game = st.session_state.turn_count >= st.session_state.target_turns * 0.6
            tired_chance = 0.3 if is_late_game else 0.1
            
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
                st.session_state.court_queue.append({
                    "speaker": "judge",
                    "text": generate_line("judge", "stock", {})
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
                st.session_state.verdict = random.choice(["not_guilty", "lenient", "guilty"])
            
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
                    st.text_input(
                        "",
                        key="player_text",
                        max_chars=50,
                        placeholder="例：いや、これは事故で… など",
                        label_visibility="collapsed",
                    )
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
                    # おやつ処理を追加
                    st.session_state.escort_script.extend(build_escort_snack_part())
                    st.session_state.escort_idx = len(st.session_state.escort_script) - 1  # ← 追加（おやつの最初から表示）
                    st.session_state.escort_phase = "showing"
                    st.rerun()
            with c2:
                if st.button("しょっぱい", use_container_width=True, key="escort_taste_salty"):
                    st.session_state.taste_pref = "salty"
                    st.session_state.escort_taste_asking = False
                    # おやつ処理を追加
                    st.session_state.escort_script.extend(build_escort_snack_part())
                    st.session_state.escort_idx = len(st.session_state.escort_script) - 1  # ← 追加
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
