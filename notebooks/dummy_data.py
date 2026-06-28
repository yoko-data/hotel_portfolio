# 表形式のデータ操作
import pandas as pd

# ランダム生成
import random

# ダミーデータの結果が常に同じ
random.seed(42)

# ----------------------------
# 客室テーブル
# ----------------------------
# roomsの中身データ
#
# 【構造メモ】
# 実際の構造をもとに設定
# 1階：和室1室（団体利用可）
# 2階：シングル・和室・ダブル・和洋室が集中
# ※4号室は縁起を考慮して欠番（実務慣習）
# ※廊下清掃30分はすべて2階廊下を想定
# シングル・和室・和室(大)は1名料金、ダブル・和洋室は２名料金で想定設定
#
# 【料金設定】
# 地方の小規模ホテルの一般的な料金帯を参考に設定
rooms = [
    # 1階（和室(大)）
    {"部屋番号": "101", "部屋タイプ": "和室", "基本料金": 7000},
    
    # 2階（シングル）
    {"部屋番号": "201", "部屋タイプ": "シングル", "基本料金": 6500},
    {"部屋番号": "202", "部屋タイプ": "シングル", "基本料金": 6500},
    {"部屋番号": "203", "部屋タイプ": "シングル", "基本料金": 6500},
    {"部屋番号": "205", "部屋タイプ": "シングル", "基本料金": 6500},
    {"部屋番号": "206", "部屋タイプ": "シングル", "基本料金": 6500},
    {"部屋番号": "207", "部屋タイプ": "シングル", "基本料金": 6500},
    {"部屋番号": "208", "部屋タイプ": "シングル", "基本料金": 6500},
    
    # 2階（和室・ダブル・和洋室）
    {"部屋番号": "209", "部屋タイプ": "和室",   "基本料金": 5500},
    {"部屋番号": "210", "部屋タイプ": "和室",   "基本料金": 5500},
    {"部屋番号": "211", "部屋タイプ": "和室",   "基本料金": 5500},
    {"部屋番号": "212", "部屋タイプ": "和室",   "基本料金": 5500},
    {"部屋番号": "213", "部屋タイプ": "ダブル",  "基本料金": 9000},
    {"部屋番号": "214", "部屋タイプ": "ダブル",  "基本料金": 9000},
    {"部屋番号": "215", "部屋タイプ": "ダブル",  "基本料金": 9000},
    {"部屋番号": "216", "部屋タイプ": "和洋室",  "基本料金": 12000},
    {"部屋番号": "217", "部屋タイプ": "和洋室",  "基本料金": 12000},
]

# DataFrameに変換してCSV保存
df_rooms = pd.DataFrame(rooms)
print(df_rooms)
df_rooms.to_csv("data/rooms.csv", index=False)

# ----------------------------
# 顧客テーブルの生成
# ----------------------------
# 【生成意図】
# リピート回数を持たせることで、常連客の傾向分析に活用できる
#
# 顧客IDをC0001〜C2000の形式で2000件生成
customer_ids = [f"c{str(i).zfill(4)}" for i in range(1, 2001)]

# 大分県で多い苗字を参照
last_names = ["渡辺", "河野", "甲斐", "後藤", "阿南",
              "佐藤", "伊藤", "高橋", "衛藤", "工藤"]
# 見本氏名 定番ネーム参照
first_names = ["太郎", "花子", "一郎", "次郎", "桃子",
               "桜子", "健太", "恵子", "幸子", "正男"]

# 苗字×名前の全組み合わせ100通りを生成
names = [f"{l}{f}" for l in last_names for f in first_names]

# 顧客データを収納する空のリストを用意
customers = []

# 2000人分の顧客データをランダムに生成
for i in range(2000):
    customers.append({
        "顧客ID": customer_ids[i],
        "名前": random.choice(names),
       # リピート回数は１回が多く、５回は少ない確率設定
        "リピート回数": random.choices([1, 2, 3, 4,5],
                                 weights=[60, 20, 10, 5, 5])[0]
    })

df_customers = pd.DataFrame(customers)
print(df_customers.head())
df_customers.to_csv("data/customers.csv", index=False)

# ----------------------------
# 予約テーブル
# ----------------------------
# 【生成の流れ】
# ① 日付ごとにシーズン区分・稼働率を決定
# ② 稼働率から当日の使用部屋数を算出
# ③ 客層をランダムに決定し、客層ごとの設定で予約データを生成
# ④ チェックイン日・チェックアウト日・プラン・経路などを組み合わせて1件の予約を作成
#
#　シーズン区分を判定する関数
def get_season(date):
    month = date.month
    day = date.day

    # GW繁忙期（スポーツ遠征・登山客が多い）
    if (month == 4 and day <= 29) or \
       (month == 4 and day >= 5):
       return "GW繁忙期"

    # 最繁忙期（正月・お盆）   
    if (month == 1 and day <= 3) or \
       (month == 8 and 13 <= day <= 16) or \
       (month == 12 and day >= 28):
        return "最繁忙期"
    
    # 閑散期
    if month in [2, 3, 6, 9]:
        return "閑散期" 

    # 繁忙期（竹の灯籠イベント『竹楽』:11月第3週末
    if month == 11 and 15 <= day <= 17:
        return "繁忙期"

    return "通常期"

# 客層毎の設定
# 夕食付きのプランもあるが、本データでは
# プラン区分を「素泊まり・朝食付き・2食付き」の3種類に統一
# 夕食のみ利用は「2食付き」に含めて集計
guest_types = {
    "ビジネス": {
        "checkin":  (17, 18),
        "checkout": (7, 8),
        "stay":     (1, 4),
        "plan":     (["素泊まり", "朝食付き", "2食付き"], [50, 30, 20]),
        "route":    (["直接", "OTA"], [40, 60])
    },
    "観光": {
        "checkin":  (15, 17),
        "checkout": (9, 10),
        "stay":     (1, 3),
        "plan":     (["素泊まり", "朝食付き", "2食付き"], [30, 50, 20]),
        "route":    (["直接", "OTA"], [40, 60])
    },
    # 【現場メモ】
    # 登山客は早朝（5〜7時）チェックアウトが多い
    # 清掃は8時以降開始のため、登山客の退室後は
    # 時間的余裕があり清掃効率が上がる
    "遠征": {
        "checkin":  (18, 19),
        "checkout": (8, 10),
        "stay":     (1, 2),
        "plan":     (["素泊まり", "朝食付き", "2食付き"], [60, 30, 20]),
        "route":    (["直接", "OTA"], [20, 80])
    },
    "登山":  {
        "checkin":  (15, 17),
        "checkout": (5, 10),
        "stay":     (1, 2),
        "plan":     (["素泊まり", "朝食付き", "2食付き"], [80, 10, 10]),
        "route":     (["直接", "OTA"], [30, 70])
    },
    "その他": {
        "checkin":  (17, 21),
        "checkout": (9, 10),
        "stay":     (1, 1),
        "plan":     (["素泊まり", "朝食付き", "2食付き"], [90, 10, 0]),
        "route":    (["直接", "OTA"], [80, 20])
    },
}

# 曜日・シーズン毎の稼働率
#
# 曜日・シーズン毎の稼働率（宿泊者がビジネス客多め）
#
# 【設定根拠】 ホテル業界7年の実務経験をもとに設定 
#
# 最繁忙期：正月・お盆は地域問わず需要が高く満室状態　
#
# GW繁忙期：スポーツ遠征・観光客が多くほぼ満室
# 　　　　　スポーツ遠征は2食付き。
#
# 繁忙期　：竹楽（地元イベント）開催週末は稼働率が上がる
# 　　　　　予約開始半年前から部屋が埋まりだし、３ヶ月前にはキャンセル待ち状態になる。
#
# 通常期　：平日は7割程度、ビジネス客利用が多く月〜木まで宿泊
#         （金曜チェックアウト→土曜休日のため木曜まで利用が多い）
#         土曜は満室、日曜は翌日仕事のため低め
#
# 閑散期　：ビジネス客の利用が落ち込む傾向
#          2・3月は年度末決算、9月は中間決算で出張が減少.
#          6月は梅雨時期で観光需要も低下
occupancy_rate = {
    "最繁忙期": {"月": 0.95, "火": 0.95, "水": 0.95, "木": 0.95,
                "金": 1.0, "土": 1.0, "日": 0.95},
    "GW繁忙期": {"月": 0.95, "火": 0.95, "水": 0.95, "木": 0.95,
                "金": 1.0, "土": 1.0, "日": 0.95},
    "繁忙期":   {"月": 0.8, "火": 0.8, "水": 0.8, "木": 0.8,
                "金": 0.9, "土": 1.0, "日": 0.8},
    "通常期":   {"月": 0.75, "火": 0.75, "水": 0.75, "木": 0.75,
                "金":0.8, "土": 1.0, "日": 0.15},
    "閑散期":   {"月": 0.5, "火": 0.5, "水": 0.5, "木": 0.5,
                "金": 0.6, "土": 0.7, "日": 0.1}
}

# 予約テーブルの生成
reservations = []
reservation_id = 1
days_of_week = ["月", "火", "水", "木","金", "土", "日"]
guest_type_list = ["ビジネス", "観光", "遠征", "登山", "その他"]
guest_weights = [40, 20, 10, 25, 5]

for date in pd.date_range("2025-01-01", "2025-12-31"):
    day_of_week = days_of_week[date.dayofweek]
    season = get_season(date)
    rate = occupancy_rate[season][day_of_week]
    
    # 登山シーズン(4・5・10・11月)の日曜日は稼働率を高く補正
    if date.month in [4, 5, 10, 11] and day_of_week == "日":
        rate = 0.85
    
    num_rooms = int(17 * rate)

    # 使用する部屋をランダムに選ぶ
    available_rooms = df_rooms.sample(n=num_rooms)

# 1件の予約データを作るための材料を準備する
    for _, room in available_rooms.iterrows():
        # お盆・正月はビジネス客・登山客はなし
        if season == "最繁忙期":
            type_list = ["ビジネス", "観光", "遠征", "登山", "その他"]
            type_weights = [0, 60, 30, 0, 10]
        elif season == "GW繁忙期":
            # GWはスポーツ遠征・観光客が多い
            type_list = ["ビジネス", "観光", "遠征", "登山", "その他"]
            type_weights = [0, 45, 45, 5, 5 ]
        else:
            type_list = guest_type_list
            type_weights = guest_weights

        guest_type = random.choices(
            type_list,
            weights=type_weights
        )[0]

        setting = guest_types[guest_type]
        stay_nights = random.randint(*setting["stay"])
        checkin_hour = random.randint(*setting["checkin"])
        checkout_hour =random.randint(*setting["checkout"])
        plan = random.choices(*setting["plan"])[0]
        
        # 正月（1/1〜1/3）は2食付きプランの需要が高い
        # 周辺飲食店が閉まっているため
        if date.month == 1 and date.day <= 3:
            plan = random.choices(
                ["素泊まり", "朝食付き", "2食付き"],
                weights=[10, 20, 70]
            )[0]
        route = random.choices(*setting["route"])[0]

# 準備した材料を使って実際に予約台帳に1行書き込む
        checkin_date = date
        checkout_date = date + pd.Timedelta(days=stay_nights)

        reservations.append({
        "予約ID": f"R{str(reservation_id).zfill(5)}",
        "顧客ID": random.choice(customer_ids),
        "部屋番号": room["部屋番号"],
        "宿泊人数": random.randint(1, 2),
        "チェックイン日": checkin_date.date(),
        "チェックアウト日": checkout_date.date(),
        "チェックイン時間":  f"{checkin_hour}:00",
        "チェックアウト時間": f"{checkout_hour}:00",
        "宿泊プラン": None if random.random() < 0.03 else plan,
        "予約経路": route,
        "客層": guest_type,
        "シーズン区分": season
})
        reservation_id += 1

df_reservations =pd.DataFrame(reservations)
print(df_reservations.head())
df_reservations.to_csv("data/reservations.csv", index=False)

# ----------------------------
# 客室清掃テーブル
# ----------------------------

# 【現場メモ】
# 実際のシフト設計では客室清掃以外に
# 廊下清掃（約25分）・大浴場清掃（約20分）も考慮が必要
# 本分析では客室清掃の集中帯に絞って最適化を提案する
# 【発展版候補】
# 連泊（宿泊日数2泊以上）の場合はエコ清掃フラグを1にする
# エコ清掃は所要時間が通常の5割程度に短縮される

# 部屋タイプ毎の清掃所要時間（分）
cleaning_time = {
    "和室（大）": (20, 30),  # お風呂付きのため和洋室と同等の清掃時間
    "シングル": (16, 20),
    "ダブル":   (20, 25),
    "和室":     (10, 15),   # お風呂なしのため清掃時間は短め
    "和洋室":    (20, 30)
}

# 各部屋の清掃データを生成
cleaning_records = []

# 予約テーブルのチェックアウト情報を元に清掃データを生成
# 予約テーブルを1行ずつ取り出す
for _, reservation in df_reservations.iterrows():

    # 部屋番号から部屋タイプを客室テーブルで調べる 
    room_type = df_rooms[
        df_rooms[ "部屋番号"] == reservation["部屋番号"]
    ]["部屋タイプ"].values[0]
    
    # 部屋タイプに対応する清掃時間の範囲を取得
    min_time, max_time = cleaning_time[room_type]

    # チェックアウト日に清掃記録を1件追加
    cleaning_records.append({
            "清掃ID": f"L{str(len(cleaning_records) + 1).zfill(5)}",
            "部屋番号": reservation["部屋番号"],
            "日付": reservation["部屋番号"],
            "所要時間": random.randint(min_time, max_time),
            "エコ清掃フラグ": 0
        })

df_cleaning = pd.DataFrame(cleaning_records)
print(df_cleaning.head())
df_cleaning.to_csv("data/cleaning.csv", index=False)