# ============================================================
# analysis.py
# 【概要】
# ホテルの予約データを分析し、清掃シフト最適化に必要な
# 情報を算出・可視化するスクリプト
#
# 【処理の流れ】
# 1. CSVデータをSQLiteに読み込む
# 2. SQLで必要なデータを抽出
# 3. pandasで加工・清掃シフト計算
# 4. matplotlibで可視化
# ============================================================
import pandas as pd
import sqlite3
import math
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['font.family'] = 'Hiragino Sans'  # 日本語文字化け防止(Mac用)

# ----------------------------
# CSVをSQLiteに読み込む
# ----------------------------
#
# データベース接続
conn = sqlite3.connect("data/hotel.db")

# CSVを読み込んでDBに保存
df_rooms = pd.read_csv("data/rooms.csv")
df_customers = pd.read_csv("data/customers.csv")
df_reservations = pd.read_csv("data/reservations.csv")

# ----------------------------
# 欠損値処理
# ----------------------------
# 【前提条件】
# 宿泊プランは記入漏れが発生することがある
# 金額データ・OTA情報照会で補完可能なケースもあるが
# 本分析では「不明」で統一して処理する
#
# 宿泊プランの欠損値を確認
print(df_reservations["宿泊プラン"].isnull().sum())

df_reservations["宿泊プラン"] = df_reservations["宿泊プラン"].fillna("不明")
df_cleaning = pd.read_csv("data/cleaning.csv")

# CSVで読み込んだデータをSQLiteのテーブルとして保存する
df_rooms.to_sql("rooms", conn, if_exists="replace", index=False)
df_customers.to_sql("customers", conn, if_exists="replace", index=False)
df_reservations.to_sql("reservations", conn,if_exists="replace", index=False)
df_cleaning.to_sql("cleaning", conn, if_exists="replace", index=False)

print("DBへの読み込み完了!")

# ----------------------------
# チェックアウト時間帯ごとの件数
# ----------------------------
# 予約テーブルからチェックアウト時間毎に件数を集計
# →何時にチェックアウトが集中しているかを把握するため
# ※チェックアウト時間は現場(清掃スタッフ）把握のみで、通常は記録には残さない
query_checkout_count = """
SELECT
    チェックアウト時間,
    COUNT(*) as 件数
FROM reservations
GROUP BY チェックアウト時間
ORDER BY チェックアウト時間
"""

df_checkout = pd.read_sql(query_checkout_count, conn)
print(df_checkout)

# ----------------------------
# 曜日毎の予約件数
# ----------------------------
# 曜日別の予約傾向を把握し、繁忙曜日の人員配置に活用する
# strftime('%w')：0=日曜、6=土曜
query_weekday_count = """
SELECT
    strftime('%w', チェックイン日) as 曜日番号,
    COUNT(*) as 予約件数
FROM reservations
GROUP BY 曜日番号
ORDER BY 曜日番号
"""

df_weekday = pd.read_sql(query_weekday_count, conn)
print(df_weekday)

# ----------------------------
# シーズン区分ごとの予約件数・売上
# ----------------------------
# シーズン別の予約傾向を把握し、繁忙期の事前人員確保に活用する
query_season_count = """
SELECT
    シーズン区分,
    COUNT(*) as 予約件数
FROM reservations
GROUP BY シーズン区分
ORDER BY 予約件数 DESC
"""

df_season = pd.read_sql(query_season_count, conn)
print(df_season)

# ----------------------------
# 客層ごとのチェックアウト時間
# ----------------------------
# 客層によってチェックアウト時間が異なるため
# 清掃開始時間の目安として把握する
query_checkout_by_guest = """
SELECT
    客層,
    チェックアウト時間,
    COUNT(*) as 件数
FROM reservations
GROUP BY 客層, チェックアウト時間
ORDER BY 客層, チェックアウト時間
"""

df_checkout_by_guest = pd.read_sql(query_checkout_by_guest, conn)
print(df_checkout_by_guest)

# ----------------------------
# 清掃シフト計算用：日付×部屋タイプ別チェックアウト件数
# ----------------------------
# 日付ごと・部屋タイプごとのチェックアウト件数を集計
# reservationsとroomsをJOINして部屋タイプ別の清掃所要時間計算に使用する
query_shift_base = """
SELECT
    r.チェックアウト日,
    rm.部屋タイプ,
    COUNT(*) as チェックアウト件数
FROM reservations r
JOIN rooms rm ON r.部屋番号 = rm.部屋番号
GROUP BY r.チェックアウト日, rm.部屋タイプ
ORDER BY r.チェックアウト日, rm.部屋タイプ
"""
df_shift = pd.read_sql(query_shift_base, conn)
print(df_shift.head(10))

# ----------------------------
# pandas加工
# ----------------------------
# チェックアウト時間を数値に変換（例：'8:00' → 8）
df_checkout["チェックアウト時間"] = df_checkout["チェックアウト時間"].str.replace(":00", "").astype(int)
df_checkout = df_checkout.sort_values("チェックアウト時間")
print(df_checkout)

# 8時以降に絞り込む（客室清掃開始時間）
df_checkout = df_checkout[df_checkout["チェックアウト時間"] >= 8]
print(df_checkout)

# 曜日番号を曜日名に変換（0=日曜、1=月曜...）
weekday_map = {
    "0": "日", "1": "月", "2": "火",
    "3": "水", "4": "木", "5": "金", "6": "土"
}
df_weekday["曜日"] = df_weekday["曜日番号"].map(weekday_map)
print(df_weekday)

# ---------------------------------
# 清掃シフト計算 STEP1
# 部屋タイプ別の清掃時間を追加・小計を計算
# ---------------------------------
# 【前提条件】
# 清掃所要時間時間は各部屋タイプの中間地を使用
# 和室(大)20〜30分 → 25分
# シングル16〜20分　→ 18分
# ダブル20〜25分　　→ 22分
# 和室10〜15分　　　→ 12分
# 和洋室20〜30分　　→ 25分

cleaning_time_map = {
    "和室（大）": 25, 
    "シングル": 18,
    "ダブル":   22,
    "和室":     12,  
    "和洋室":    25
}

# 部屋タイプに対応する清掃所要時間を列として追加
df_shift["清掃所要時間(分)"] = df_shift["部屋タイプ"].map(cleaning_time_map)

# チェックアウト件数　×　清掃所要時間　=　小計
df_shift["小計(分)"] = df_shift["チェックアウト件数"] * df_shift["清掃所要時間(分)"] 

print(df_shift)

# ----------------------------
# 清掃シフト計算 STEP2
# 日付ごとに合計 → 必要人数を計算
# ----------------------------
# 日付毎に小計を合算
df_daily = df_shift.groupby("チェックアウト日")["小計(分)"].sum().reset_index()
df_daily.rename(columns={"小計(分)": "客室清掃合計(分)"}, inplace=True)

# 固定作業時間を追加(廊下の掃除機30分・大浴場清掃20分)
# 廊下清掃30分・大浴場清掃20分は毎日固定で発生
df_daily["固定作業(分)"] = 50
df_daily["総清掃所要時間(分)"] = df_daily["客室清掃合計(分)"] + df_daily["固定作業(分)"]

# 必要人数を計算(切り上げ)
# スタッフ一人あたりの稼働時間：240分(休憩なし)
# ※実務では勤務が午前〜午後に跨ぐ場合、30分休憩を差し引き210分が現実的
WORK_MINUTES = 240
df_daily["必要人数"] = df_daily["総清掃所要時間(分)"].apply(
    lambda x: math.ceil(x / WORK_MINUTES)
)

print(df_daily)

# 必要人数が最大の日を確認
print(df_daily["必要人数"].max())

# 必要人数が３人以上の日があるか確認
print(df_daily[df_daily["必要人数"] >= 3])

# ============================================================
# 可視化
# 【概要】
# 以下のグラフをmatplotlibで描画する
# STEP1：チェックアウト時間帯ごとの件数（棒グラフ）
# STEP2：曜日別予約件数（棒グラフ）
# STEP3：シーズン別予約件数（棒グラフ）
# STEP4：月別平均清掃スタッフ必要人数（棒グラフ）
# STEP5：月別予約件数の推移（折れ線グラフ）
# STEP6：客層別チェックアウト時間（グループ棒グラフ）
# ============================================================
#
# ----------------------------------
# 可視化 STEP1
# チェックアウト時間帯ごとの件数（棒グラフ）
# ----------------------------------
plt.figure(figsize=(8, 5))
plt.bar(df_checkout["チェックアウト時間"], df_checkout["件数"], color="steelblue")

plt.title("チェックアウト時間帯毎の件数")
plt.xlabel("チェックアウト時間")
plt.ylabel("件数")
plt.xticks([8, 9, 10]) # x軸の目盛りを指定
plt.tight_layout()
plt.show()

# ----------------------------
# 可視化 STEP2
# 曜日別予約件数（棒グラフ）
# ----------------------------
# 各棒に色
colors = ["#e15759", "#4e79a7", "#f28e2b", "#76b7b2", 
          "#59a14f", "#edc948", "#b07aa1"]
# 日・月・火・水・木・金・土　の順
plt.figure(figsize=(8, 5))
plt.bar(df_weekday["曜日"], df_weekday["予約件数"], color=colors)

plt.title("曜日別予約件数")
plt.xlabel("曜日")
plt.ylabel("予約件数")
plt.tight_layout()
plt.show()

# ----------------------------
# 可視化 STEP3
# シーズン別予約件数（棒グラフ）
# ----------------------------
plt.figure(figsize=(8, 5))
plt.bar(df_season["シーズン区分"], df_season["予約件数"], color="mediumseagreen")

plt.title("シーズン別予約件数")
plt.xlabel("シーズン区分")
plt.ylabel("予約件数")
plt.tight_layout()
plt.show()

# ----------------------------
# 可視化 STEP4
# 月別平均必要人数（棒グラフ）
# ----------------------------
# チェックアウト日を日付型に変換して月を抽出 
df_daily["チェックアウト日"] = pd.to_datetime(df_daily["チェックアウト日"])
df_daily["月"] = df_daily["チェックアウト日"].dt.month 

# 月別に必要人数の平均を計算 
df_monthly = df_daily.groupby("月")["必要人数"].mean().reset_index()
plt.figure(figsize=(10, 5))
plt.bar(df_monthly["月"], df_monthly["必要人数"], color="coral")

plt.title("月別清掃スタッフ必要人数")
plt.xlabel("月")
plt.ylabel("必要人数")
plt.xticks(range(1, 13))  # 1〜12月を表示
plt.tight_layout()
plt.show()

# ----------------------------
# 可視化 STEP5
# 月別予約件数の推移（折れ線グラフ）
# ----------------------------
# 月別に予約件数を集計
df_reservations["チェックイン日"] = pd.to_datetime(df_reservations["チェックイン日"])
df_reservations["月"] = df_reservations["チェックイン日"].dt.month
df_monthly_count = df_reservations.groupby("月").size().reset_index(name="予約件数")

plt.figure(figsize=(10, 5))
plt.plot(df_monthly_count["月"],df_monthly_count["予約件数"],
         color="steelblue", marker="o")  # marker="o"で点を表示

plt.title("月別予約件数の推移")
plt.xlabel("月")
plt.ylabel("予約件数")
plt.xticks(range(1, 13))
plt.tight_layout()
plt.show()

# ----------------------------
# 可視化 STEP6
# 客層別チェックアウト時間（グループ棒グラフ）
# ----------------------------
# 【現場メモ】
# 実際はビジネス客も金曜・土曜宿泊の場合
# 9・10時チェックアウトが一部存在する
# 本データでは7・8時に集中する設定としている
df_pivot = df_checkout_by_guest.pivot(
    index="チェックアウト時間",
    columns="客層",
    values="件数",
).fillna(0)

df_pivot.plot(kind="bar", figsize=(10, 5), colormap="tab10")
plt.title("客層別チェックアウト時間")
plt.xlabel("チェックアウト時間")
plt.ylabel("件数")
plt.legend(title="客層")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()