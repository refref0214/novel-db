import streamlit as st
import pandas as pd
import uuid # IDを自動生成するため
import google_db # スプレッドシート接続用

# ページ設定
st.set_page_config(page_title="登場人物DB（クラウド版）", layout="wide")
st.title("☁️ 登場人物データベース (Google Sheets)")

# セッションステート初期化
if "current_mode" not in st.session_state:
    st.session_state.current_mode = "全キャラ一覧"
if "editing_id" not in st.session_state:
    st.session_state.editing_id = None
if "char_cache" not in st.session_state:
    st.session_state.char_cache = [] # データを一時保存して高速化
if "new_uuid" not in st.session_state:
    st.session_state.new_uuid = str(uuid.uuid4())

# --- ヘルパー関数 ---
def load_data():
    """Googleからデータを再読み込み"""
    with st.spinner('Googleからデータを読み込んでいます...'):
        st.session_state.char_cache = google_db.load_all_characters()

def go_to_edit(char_id):
    st.session_state.editing_id = char_id
    st.session_state.current_mode = "既存キャラの編集"

# --- サイドバー ---
st.sidebar.header("メニュー")

# リロードボタン
if st.sidebar.button("🔄 データを更新"):
    st.cache_data.clear()
    load_data()
    st.rerun()

operation = st.sidebar.radio(
    "操作を選択", 
    ["全キャラ一覧", "新規作成", "既存キャラの編集"],
    key="current_mode"
)

# 初回起動時にデータをロード
if not st.session_state.char_cache:
    load_data()

all_chars = st.session_state.char_cache
current_data = {}

# ==========================================
# 1. 全キャラ一覧モード
# ==========================================
if operation == "全キャラ一覧":
    st.header("🗂️ 全キャラクター一覧")
    
    if not all_chars:
        st.info("データがありません。「新規作成」してください。")
    else:
        # テーブル用データ作成
        df_list = []
        for c in all_chars:
            prof = c["full_data"].get("profile", {})
            df_list.append({
                "ID": c["ID"],
                "氏名": c["氏名"],
                "年齢": prof.get("age_info", ""),
                "画像": c["画像URL"]
            })
        df_all = pd.DataFrame(df_list)

        # ① リスト表示
        st.subheader("📋 リスト (行を選択して編集)")
        event = st.dataframe(
            df_all[["氏名", "年齢", "ID"]],
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            on_select="rerun"
        )
        
        if len(event.selection.rows) > 0:
            idx = event.selection.rows[0]
            target = df_list[idx]
            st.info(f"選択中: **{target['氏名']}**")
            st.button(f"📝 {target['氏名']} の編集画面へ移動", type="primary", on_click=go_to_edit, args=(target["ID"],))

        st.markdown("---")

        # ② ギャラリー表示
        st.subheader("🖼️ ギャラリー")
        cols = st.columns(4)
        for idx, char in enumerate(df_list):
            with cols[idx % 4]:
                with st.container(border=True):
                    img_url = char["画像"]
                    if img_url:
                        st.image(img_url, use_container_width=True)
                    else:
                        st.markdown("""<div style="height:100px;background:#eee;color:#888;display:flex;align-items:center;justify_content:center;">No Image</div>""", unsafe_allow_html=True)
                    st.markdown(f"**{char['氏名']}**")
                    st.button("編集", key=f"btn_{char['ID']}", on_click=go_to_edit, args=(char["ID"],))


# ==========================================
# 2. 新規作成・編集モード
# ==========================================
else:
    target_id = None
    
    if operation == "既存キャラの編集":
        # IDリストを作る
        id_map = {c["ID"]: c["氏名"] for c in all_chars}
        id_list = list(id_map.keys())
        
        if id_list:
            # セレクトボックス
            index = 0
            if st.session_state.editing_id in id_list:
                index = id_list.index(st.session_state.editing_id)
            
            def on_change_select():
                st.session_state.editing_id = st.session_state.selectbox_id
            
            selected_id = st.sidebar.selectbox(
                "編集するキャラ", 
                id_list, 
                format_func=lambda x: id_map[x],
                index=index,
                key="selectbox_id",
                on_change=on_change_select
            )
            target_id = selected_id
            
            # データを取り出す
            for c in all_chars:
                if c["ID"] == target_id:
                    current_data = c["full_data"]
                    break
        else:
            st.warning("データがありません")

    elif operation == "新規作成":
        st.sidebar.info("新規作成中")
        current_data = {}
        # 新規ID
        target_id = st.session_state.new_uuid

    # --- データ取得ヘルパー ---
    def get_val(path, key, default=""):
        d = current_data
        for p in path:
            d = d.get(p, {})
        if d is None: return default
        return d.get(key, default)

    # ==========================
    # 入力フォーム (ローカル版と完全一致)
    # ==========================
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["基本プロフィール", "年表(履歴)", "外見・環境・性格等", "喜怒哀楽", "人生における作品の位置"])

    # --- Tab 1: 基本プロフィール ---
    with tab1:
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("#### 顔写真")
            st.caption("※Googleドライブの画像の共有リンクなどを貼ってください")
            image_file = st.text_input("画像URL", value=get_val(["profile"], "image_file", ""))
            
            if image_file:
                st.image(image_file, use_container_width=True, caption="プレビュー")
            else:
                st.info("画像なし")

        with col2:
            st.markdown("#### 基本情報")
            name = st.text_input("氏名", value=get_val(["profile"], "name", ""))
            kana = st.text_input("ふりがな", value=get_val(["profile"], "kana", ""))
            
            col2_1, col2_2 = st.columns(2)
            with col2_1:
                 age_info = st.text_input("年齢・生年月日", value=get_val(["profile"], "age_info", ""))
            with col2_2:
                 gender = st.selectbox("性別", ["男性", "女性", "その他", "不明"], index=["男性", "女性", "その他", "不明"].index(get_val(["profile"], "gender", "男性")) if get_val(["profile"], "gender", "男性") in ["男性", "女性", "その他", "不明"] else 0)
            
            address = st.text_input("現住所", value=get_val(["profile"], "address", ""))

        st.markdown("---")
        
        col_mot, col_pr = st.columns(2)
        with col_mot:
            motivation = st.text_area("志望動機", value=get_val(["essay"], "motivation", ""), height=150)
        with col_pr:
            self_pr = st.text_area("自己PR", value=get_val(["essay"], "self_pr", ""), height=150)

        st.write("")
        st.markdown("**免許・資格**") 
        st.caption("年・月と資格内容を入力してください。下の「＋」で行を追加できます。")
        
        licenses_data = current_data.get("licenses", [])
        if not licenses_data:
            df_licenses = pd.DataFrame([{"date": "", "content": ""}], columns=["date", "content"])
        else:
            df_licenses = pd.DataFrame(licenses_data)

        edited_licenses = st.data_editor(
            df_licenses,
            num_rows="dynamic",
            column_config={
                "date": st.column_config.TextColumn("年月", width="small", help="例: 2015年4月"),
                "content": st.column_config.TextColumn("免許・資格の内容", width="large"),
            },
            use_container_width=True,
            key="licenses_editor"
        )

    # --- Tab 2: 年表（無限追加可能） ---
    with tab2:
        st.markdown("### 学歴・職歴・出来事")
        st.info("下の表に直接入力してください。一番下の「＋」で行を追加できます。")
        
        timeline_data = current_data.get("timeline", [])
        if not timeline_data:
            df_timeline = pd.DataFrame([{"date": "", "event": "", "note": ""}], columns=["date", "event", "note"])
        else:
            df_timeline = pd.DataFrame(timeline_data)

        edited_df = st.data_editor(
            df_timeline,
            num_rows="dynamic",
            column_config={
                "date": st.column_config.TextColumn("年月", width="small", help="例: 2010年4月"),
                "event": st.column_config.TextColumn("出来事", width="large"),
                "note": st.column_config.TextColumn("備考・詳細", width="medium"),
            },
            use_container_width=True,
            key="timeline_editor"
        )

    # --- Tab 3: 外見・環境・性格等 ---
    with tab3:
        col_app, col_env, col_pers = st.columns(3)
        
        with col_app:
            st.subheader("外見 (Appearance)")
            height = st.text_input("身長", value=get_val(["appearance"], "身長", ""))
            weight = st.text_input("体重", value=get_val(["appearance"], "体重", ""))
            hair = st.text_input("髪型", value=get_val(["appearance"], "髪型", ""))
            face = st.text_area("顔の特徴", value=get_val(["appearance"], "顔の特徴", ""))
            medical = st.text_area("既往症", value=get_val(["appearance"], "既往症", ""), help="病歴やアレルギーなど")
            rewards = st.text_area("賞罰", value=get_val(["appearance"], "賞罰", ""), help="受賞歴や前科など")
            
        with col_env:
            st.subheader("環境 (Environment)")
            family = st.text_area("家族構成", value=get_val(["environment"], "家族構成", ""))
            love = st.text_input("恋人の有無", value=get_val(["environment"], "恋人の有無", ""))
            hobby = st.text_area("趣味", value=get_val(["environment"], "趣味", ""))
            habits = st.text_area("嗜好歴・喫煙・飲酒歴", value=get_val(["environment"], "嗜好", ""))

        with col_pers:
            st.subheader("性格 (Personality)")
            strengths = st.text_area("長所", value=get_val(["personality"], "長所", ""), height=150)
            weaknesses = st.text_area("短所", value=get_val(["personality"], "短所", ""), height=150)

    # --- Tab 4: 喜怒哀楽 ---
    with tab4:
        # ★ここをローカル版の質問文に完全に戻しました
        q_joy = "この人物が作品に登場するまでの人生でいちばん嬉しかったことはなんですか"
        ans_joy = st.text_area(q_joy, value=get_val(["emotions"], q_joy, ""), height=150)

        q_sad = "この人物が作品に登場するまでの人生でいちばん悲しかったことはなんですか"
        ans_sad = st.text_area(q_sad, value=get_val(["emotions"], q_sad, ""), height=150)

        q_anger = "この人物が作品に登場するまでの人生でいちばん怒ったことはなんですか"
        ans_anger = st.text_area(q_anger, value=get_val(["emotions"], q_anger, ""), height=150)

        q_fun = "この人物が作品に登場するまでの人生でいちばん楽しかったことはなんですか"
        ans_fun = st.text_area(q_fun, value=get_val(["emotions"], q_fun, ""), height=150)

        q_suf = "この人物が作品に登場するまでの人生でいちばん苦しかったことはなんですか"
        ans_suf = st.text_area(q_suf, value=get_val(["emotions"], q_suf, ""), height=150)

    # --- Tab 5: 人生における作品の位置 ---
    with tab5:
        # ★ここもローカル版の質問文に戻しました
        q_role1 = "この人物が作品に登場することは、それまでの人生でどんな位置にありますか"
        ans_role1 = st.text_area(q_role1, value=get_val(["story_role"], q_role1, ""), height=100)

        q_role2 = "この人物の、この作品での目的はどんなことですか"
        ans_role2 = st.text_area(q_role2, value=get_val(["story_role"], q_role2, ""), height=100)

        q_role3 = "この人物がこれからの人生で最も起こってほしくないことはどんなことですか"
        ans_role3 = st.text_area(q_role3, value=get_val(["story_role"], q_role3, ""), height=100)

        q_role4 = "この人物がこれからの人生で最も起きてほしいことはどんなことですか"
        ans_role4 = st.text_area(q_role4, value=get_val(["story_role"], q_role4, ""), height=100)

        st.markdown("---")
        st.markdown("### その他")
        q_other = "設定事項（どんなことでも）"
        ans_other = st.text_area(q_other, value=get_val(["others"], "note", ""), height=200)

    # --- 保存ボタン ---
    st.markdown("---")
    if st.button("☁️ Googleスプレッドシートに保存する", type="primary"):
        with st.spinner("保存中..."):
            # データ整形
            clean_timeline = edited_df.to_dict(orient="records")
            clean_timeline = [row for row in clean_timeline if row["date"] or row["event"]]

            clean_licenses = edited_licenses.to_dict(orient="records")
            clean_licenses = [row for row in clean_licenses if row["date"] or row["content"]]

            # 全データ構築
            full_data = {
                "profile": {
                    "name": name,
                    "kana": kana,
                    "image_file": image_file, # URL
                    "age_info": age_info,
                    "gender": gender,
                    "address": address,
                },
                "licenses": clean_licenses,
                "essay": {
                    "motivation": motivation,
                    "self_pr": self_pr
                },
                "timeline": clean_timeline,
                "appearance": {
                    "身長": height,
                    "体重": weight,
                    "髪型": hair,
                    "顔の特徴": face,
                    "既往症": medical,
                    "賞罰": rewards
                },
                "environment": {
                    "家族構成": family,
                    "恋人の有無": love,
                    "趣味": hobby,
                    "嗜好": habits
                },
                "personality": {
                    "長所": strengths,
                    "短所": weaknesses
                },
                "emotions": {
                    q_joy: ans_joy,
                    q_sad: ans_sad,
                    q_anger: ans_anger,
                    q_fun: ans_fun,
                    q_suf: ans_suf
                },
                "story_role": {
                    q_role1: ans_role1,
                    q_role2: ans_role2,
                    q_role3: ans_role3,
                    q_role4: ans_role4
                },
                "others": {
                    "note": ans_other
                }
            }
            
            # Googleに保存
            success = google_db.save_character(target_id, full_data)
            
            if success:
                st.success("保存完了！")
                st.cache_data.clear() # キャッシュクリア
                # 新規作成ならIDリセット
                if operation == "新規作成":
                    st.session_state.new_uuid = str(uuid.uuid4())
                    # 新規保存後は一覧に戻るか、編集モードに切り替えるなど
                    st.session_state.current_mode = "全キャラ一覧"
                
                load_data() # データ再読み込み
                st.rerun()
            else:
                st.error("保存に失敗しました。接続設定を確認してください。")