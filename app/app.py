import sqlite3
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import math
import streamlit as st

matplotlib.rcParams['font.family'] = 'Hiragino Sans'

st.set_page_config(
    page_title="ホテル清掃シフト最適化ダッシュボード",
    layout="wide"
)

st.title("ホテル清掃シフト最適化ダッシュボード")

# ----------------------------
# データ読み込み・加工
# ----------------------------
conn = sqlite3.connect("data/hotel.db")

df_reservations = pd.read_sql("SELECT * FROM reservations", conn)
df_rooms = pd.read_sql("SELECT * FROM rooms", conn)

df_checkout_by_guest = pd.read_sql("""
    SELECT 客層, チェックアウト時間, COUNT(*) as 件数
    FROM reservations
    GROUP BY 客層, チェックアウト時間
    ORDER BY 客層, チェックアウト時間
""", conn)

# 月別予約件数
df_reservations["チェックイン日"] = pd.to_datetime(df_reservations["チェックイン日"])
df_reservations["月"] = df_reservations["チェックイン日"].dt.month
df_monthly_count = df_reservations.groupby("月").size().reset_index(name="予約件数")

# シーズン別
df_season = pd.read_sql("""
    SELECT シーズン区分, COUNT(*) as 予約件数
    FROM reservations
    GROUP BY シーズン区分
    ORDER BY 予約件数 DESC
""", conn)

# 曜日別
df_weekday = pd.read_sql("""
    SELECT strftime('%w', チェックイン日) as 曜日番号, COUNT(*) as 予約件数
    FROM reservations
    GROUP BY 曜日番号
    ORDER BY 曜日番号
""", conn)
weekday_map = {"0": "日", "1": "月", "2": "火", "3": "水", "4": "木", "5": "金", "6": "土"}
df_weekday["曜日番号"] = df_weekday["曜日番号"].astype(str)
df_weekday["曜日"] = df_weekday["曜日番号"].map(weekday_map)

# チェックアウト時間
df_checkout = pd.read_sql("SELECT チェックアウト時間, COUNT(*) as 件数 FROM reservations GROUP BY チェックアウト時間", conn)
df_checkout["チェックアウト時間"] = df_checkout["チェックアウト時間"].str.replace(":00", "").astype(int)
df_checkout = df_checkout[df_checkout["チェックアウト時間"] >= 8]

# 客層別チェックアウト時間
df_checkout_by_guest["チェックアウト時間"] = df_checkout_by_guest["チェックアウト時間"].str.replace(":00", "").astype(int)
df_checkout_by_guest = df_checkout_by_guest.sort_values("チェックアウト時間")
df_pivot = df_checkout_by_guest.pivot(
    index="チェックアウト時間",
    columns="客層",
    values="件数"
).fillna(0)
df_pivot.index = df_pivot.index.astype(str) + ":00"

# 清掃シフト計算
query_shift = """
    SELECT r.チェックアウト日, rm.部屋タイプ, COUNT(*) as チェックアウト件数
    FROM reservations r
    JOIN rooms rm ON r.部屋番号 = rm.部屋番号
    GROUP BY r.チェックアウト日, rm.部屋タイプ
    ORDER BY r.チェックアウト日, rm.部屋タイプ
"""
df_shift = pd.read_sql(query_shift, conn)
cleaning_time_map = {"シングル": 18, "ダブル": 22, "和室": 12, "和洋室": 25, "和室（大）": 25}
df_shift["清掃所要時間(分)"] = df_shift["部屋タイプ"].map(cleaning_time_map)
df_shift["小計(分)"] = df_shift["チェックアウト件数"] * df_shift["清掃所要時間(分)"]
df_daily = df_shift.groupby("チェックアウト日")["小計(分)"].sum().reset_index()
df_daily.rename(columns={"小計(分)": "客室清掃合計(分)"}, inplace=True)
df_daily["固定作業(分)"] = 50
df_daily["総清掃所要時間(分)"] = df_daily["客室清掃合計(分)"] + df_daily["固定作業(分)"]
df_daily["必要人数"] = df_daily["総清掃所要時間(分)"].apply(lambda x: math.ceil(x / 240))
df_daily["チェックアウト日"] = pd.to_datetime(df_daily["チェックアウト日"])
df_daily["月"] = df_daily["チェックアウト日"].dt.month
df_monthly = df_daily.groupby("月")["必要人数"].mean().reset_index()

colors = ["#e15759", "#4e79a7", "#f28e2b", "#76b7b2", "#59a14f", "#edc948", "#b07aa1"]

# ----------------------------
# グラフ表示
# ----------------------------

# 【2列】月別予約件数 | シーズン別予約件数
st.divider()
col1, col2 = st.columns(2)

with col1:
    st.subheader("月別予約件数の推移")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(df_monthly_count["月"], df_monthly_count["予約件数"],
            color="steelblue", marker="o")
    ax.set_xlabel("月")
    ax.set_ylabel("予約件数")
    ax.set_xticks(range(1, 13))
    st.pyplot(fig)
    st.caption("4月〜5月（GW・登山シーズン）に予約が集中し、2〜3月は閑散期として落ち込む傾向がある。")

with col2:
    st.subheader("シーズン別予約件数")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(df_season["シーズン区分"], df_season["予約件数"], color="mediumseagreen")
    ax.set_xlabel("シーズン区分")
    ax.set_ylabel("予約件数")
    st.pyplot(fig)
    st.caption("通常期が件数は最も多いが、最繁忙期・繁忙期はほぼ満室状態のため、限られた時間での清掃効率が特に重要になる時期。最繁忙期・繁忙期の詳細は後述『最繁忙期・繁忙期の客層別グラフ』を追加予定。")

# 【1列】曜日別予約件数
st.subheader("曜日別予約件数")
fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(df_weekday["曜日"], df_weekday["予約件数"], color=colors)
ax.set_xlabel("曜日")
ax.set_ylabel("予約件数")
st.pyplot(fig)
st.caption("土曜日に最も予約が集中。平日はビジネス客、週末は観光・遠征・登山客が多い傾向がある。曜日毎の客層別の詳細は後述、『曜日予約の客層グラフ』を追加予定。")

# 【2列】チェックアウト時間 | 客層別チェックアウト時間
st.divider()
col3, col4 = st.columns(2)

with col3:
    st.subheader("チェックアウト時間毎の件数")
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(df_checkout["チェックアウト時間"], df_checkout["件数"], color="steelblue")
    ax.set_xlabel("チェックアウト時間")
    ax.set_ylabel("件数")
    ax.set_xticks([8, 9, 10])
    st.pyplot(fig)
    st.caption("清掃開始の8時以降を集計(現場把握の予測データ)。8・10時に件数が集中しており、ピーク時の8時と10時に人員配置が必要。")

with col4:
    st.subheader("客層別チェックアウト時間")
    fig, ax = plt.subplots(figsize=(6, 4))
    df_pivot.plot(kind="bar", ax=ax, colormap="tab10")
    ax.set_xlabel("チェックアウト時間")
    ax.set_ylabel("件数")
    ax.legend(title="客層")
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)
    st.caption("客層によってチェックアウト時間の傾向が異なる。ビジネス客は7〜8時、観光客は9〜10時。遠征客は目的により8〜10時とバラつきがある。登山客は早朝チェックアウトが多い。")

# 【1列】月別平均清掃スタッフ必要人数
st.divider()
st.subheader("月別平均清掃スタッフ必要人数")
fig, ax = plt.subplots(figsize=(12, 4))
ax.bar(df_monthly["月"], df_monthly["必要人数"], color="coral")
ax.set_xlabel("月")
ax.set_ylabel("平均必要人数")
ax.set_xticks(range(1, 13))
st.pyplot(fig)
st.caption("4・5月(GW・登山シーズン)と10・11月(紅葉シーズン)に必要人数が増加。平日はビジネス客が多く清掃効率が高い傾向がある。繁忙期に合わせた事前の人員確保が重要。")