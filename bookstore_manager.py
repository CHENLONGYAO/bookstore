import sqlite3
from typing import Tuple, Optional
from datetime import datetime

# 常數
DB_NAME = "bookstore.db"
DATE_FORMAT = "%Y-%m-%d"

def connect_db() -> sqlite3.Connection:
    """建立並返回 SQLite 資料庫連線，設置 row_factory。

    返回:
        sqlite3.Connection: 資料庫連線物件。
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db(conn: sqlite3.Connection) -> None:
    """初始化資料庫表格並插入初始資料（若表格不存在）。

    參數:
        conn (sqlite3.Connection): 資料庫連線物件。
    """
    with conn:
        cursor = conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS member (
                mid TEXT PRIMARY KEY,
                mname TEXT NOT NULL,
                mphone TEXT NOT NULL,
                memail TEXT
            );

            CREATE TABLE IF NOT EXISTS book (
                bid TEXT PRIMARY KEY,
                btitle TEXT NOT NULL,
                bprice INTEGER NOT NULL,
                bstock INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sale (
                sid INTEGER PRIMARY KEY AUTOINCREMENT,
                sdate TEXT NOT NULL,
                mid TEXT NOT NULL,
                bid TEXT NOT NULL,
                sqty INTEGER NOT NULL,
                sdiscount INTEGER NOT NULL,
                stotal INTEGER NOT NULL
            );

            INSERT OR IGNORE INTO member VALUES
                ('M001', 'Alice', '0912-345678', 'alice@example.com'),
                ('M002', 'Bob', '0923-456789', 'bob@example.com'),
                ('M003', 'Cathy', '0934-567890', 'cathy@example.com');

            INSERT OR IGNORE INTO book VALUES
                ('B001', 'Python Programming', 600, 50),
                ('B002', 'Data Science Basics', 800, 30),
                ('B003', 'Machine Learning Guide', 1200, 20);

            INSERT OR IGNORE INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) VALUES
                ('2024-01-15', 'M001', 'B001', 2, 100, 1100),
                ('2024-01-16', 'M002', 'B002', 1, 50, 750),
                ('2024-01-17', 'M001', 'B003', 3, 200, 3400),
                ('2024-01-18', 'M003', 'B001', 1, 0, 600);
        """)
        conn.commit()

def validate_date(sdate: str) -> bool:
    """驗證日期格式 (YYYY-MM-DD)。

    參數:
        sdate (str): 要驗證的日期字串。

    返回:
        bool: 若格式正確則返回 True，否則返回 False。
    """
    if len(sdate) != 10 or sdate.count('-') != 2:
        return False
    try:
        datetime.strptime(sdate, DATE_FORMAT)
        return True
    except ValueError:
        return False

def add_sale(conn: sqlite3.Connection, sdate: str, mid: str, bid: str, sqty: int, sdiscount: int) -> Tuple[bool, str]:
    """新增銷售記錄，驗證輸入並更新庫存。

    參數:
        conn (sqlite3.Connection): 資料庫連線物件。
        sdate (str): 銷售日期 (YYYY-MM-DD)。
        mid (str): 會員編號。
        bid (str): 書籍編號。
        sqty (int): 購買數量。
        sdiscount (int): 折扣金額。

    返回:
        Tuple[bool, str]: (是否成功, 訊息)。
    """
    if not validate_date(sdate):
        return False, "錯誤：無效的日期格式，必須為 YYYY-MM-DD"

    with conn:
        cursor = conn.cursor()

        # 檢查會員是否存在
        cursor.execute("SELECT mid FROM member WHERE mid = ?", (mid,))
        if not cursor.fetchone():
            return False, "錯誤：會員編號或書籍編號無效"

        # 檢查書籍是否存在並取得價格和庫存
        cursor.execute("SELECT bprice, bstock FROM book WHERE bid = ?", (bid,))
        book = cursor.fetchone()
        if not book:
            return False, "錯誤：會員編號或書籍編號無效"

        bprice, bstock = book['bprice'], book['bstock']

        # 驗證數量和庫存
        if sqty <= 0:
            return False, "錯誤：數量必須為正整數"
        if sqty > bstock:
            return False, f"錯誤：書籍庫存不足 (現有庫存: {bstock})"

        # 驗證折扣
        if sdiscount < 0:
            return False, "錯誤：折扣金額不能為負數"

        # 計算總額
        stotal = (bprice * sqty) - sdiscount

        try:
            # 插入銷售記錄
            cursor.execute(
                "INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) VALUES (?, ?, ?, ?, ?, ?)",
                (sdate, mid, bid, sqty, sdiscount, stotal)
            )
            # 更新書籍庫存
            cursor.execute("UPDATE book SET bstock = bstock - ? WHERE bid = ?", (sqty, bid))
            conn.commit()
            return True, f"銷售記錄已新增！(銷售總額: {stotal:,})"
        except sqlite3.Error as e:
            conn.rollback()
            return False, f"錯誤：資料庫操作失敗 - {str(e)}"

def print_sale_report(conn: sqlite3.Connection) -> None:
    """查詢並顯示所有銷售報表，按銷售編號排序。

    參數:
        conn (sqlite3.Connection): 資料庫連線物件。
    """
    with conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.sid, s.sdate, m.mname, b.btitle, b.bprice, s.sqty, s.sdiscount, s.stotal
            FROM sale s
            JOIN member m ON s.mid = m.mid
            JOIN book b ON s.bid = b.bid
            ORDER BY s.sid
        """)
        sales = cursor.fetchall()

        print("\n==================== 銷售報表 ====================")
        for i, sale in enumerate(sales, 1):
            print(f"\n銷售 #{i}")
            print(f"銷售編號: {sale['sid']}")
            print(f"銷售日期: {sale['sdate']}")
            print(f"會員姓名: {sale['mname']}")
            print(f"書籍標題: {sale['btitle']}")
            print("-" * 50)
            print("單價\t數量\t折扣\t小計")
            print("-" * 50)
            print(f"{sale['bprice']:,}\t{sale['sqty']}\t{sale['sdiscount']:,}\t{sale['stotal']:,}")
            print("-" * 50)
            print(f"銷售總額: {sale['stotal']:,}")
            print("=" * 50)

def update_sale(conn: sqlite3.Connection) -> None:
    """顯示銷售記錄列表，更新選擇的銷售記錄的折扣和總額。

    參數:
        conn (sqlite3.Connection): 資料庫連線物件。
    """
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT s.sid, m.mname, s.sdate FROM sale s JOIN member m ON s.mid = m.mid ORDER BY s.sid")
        sales = cursor.fetchall()

        if not sales:
            print("無銷售記錄可更新")
            return

        print("\n======== 銷售記錄列表 ========")
        for i, sale in enumerate(sales, 1):
            print(f"{i}. 銷售編號: {sale['sid']} - 會員: {sale['mname']} - 日期: {sale['sdate']}")
        print("=" * 32)

        choice = input("請選擇要更新的銷售編號 (輸入數字或按 Enter 取消): ").strip()
        if not choice:
            return

        try:
            choice = int(choice)
            if choice < 1 or choice > len(sales):
                print("錯誤：請輸入有效的數字")
                return
            sid = sales[choice - 1]['sid']
        except ValueError:
            print("錯誤：請輸入有效的數字")
            return

        while True:
            try:
                sdiscount = int(input("請輸入新的折扣金額：").strip())
                if sdiscount < 0:
                    print("錯誤：折扣金額不能為負數，請重新輸入")
                    continue
                break
            except ValueError:
                print("錯誤：折扣金額必須為整數，請重新輸入")

        try:
            # 取得當前銷售記錄的詳細資訊
            cursor.execute("""
                SELECT s.sqty, b.bprice
                FROM sale s
                JOIN book b ON s.bid = b.bid
                WHERE s.sid = ?
            """, (sid,))
            sale = cursor.fetchone()
            if sale:
                stotal = (sale['bprice'] * sale['sqty']) - sdiscount
                cursor.execute(
                    "UPDATE sale SET sdiscount = ?, stotal = ? WHERE sid = ?",
                    (sdiscount, stotal, sid)
                )
                conn.commit()
                print(f"=> 銷售編號 {sid} 已更新！(銷售總額: {stotal:,})")
        except sqlite3.Error as e:
            conn.rollback()
            print(f"錯誤：資料庫操作失敗 - {str(e)}")

def delete_sale(conn: sqlite3.Connection) -> None:
    """顯示銷售記錄列表並刪除選擇的銷售記錄。

    參數:
        conn (sqlite3.Connection): 資料庫連線物件。
    """
    with conn:
        cursor = conn.cursor()
        cursor.execute("SELECT s.sid, m.mname, s.sdate FROM sale s JOIN member m ON s.mid = m.mid ORDER BY s.sid")
        sales = cursor.fetchall()

        if not sales:
            print("無銷售記錄可刪除")
            return

        print("\n======== 銷售記錄列表 ========")
        for i, sale in enumerate(sales, 1):
            print(f"{i}. 銷售編號: {sale['sid']} - 會員: {sale['mname']} - 日期: {sale['sdate']}")
        print("=" * 32)

        choice = input("請選擇要刪除的銷售編號 (輸入數字或按 Enter 取消): ").strip()
        if not choice:
            return

        try:
            choice = int(choice)
            if choice < 1 or choice > len(sales):
                print("錯誤：請輸入有效的數字")
                return
            sid = sales[choice - 1]['sid']
        except ValueError:
            print("錯誤：請輸入有效的數字")
            return

        try:
            cursor.execute("DELETE FROM sale WHERE sid = ?", (sid,))
            conn.commit()
            print(f"=> 銷售編號 {sid} 已刪除")
        except sqlite3.Error as e:
            conn.rollback()
            print(f"錯誤：資料庫操作失敗 - {str(e)}")

def main() -> None:
    """程式主流程，包含選單迴圈和各功能呼叫。"""
    conn = connect_db()
    initialize_db(conn)

    while True:
        print("\n***************選單***************")
        print("1. 新增銷售記錄")
        print("2. 顯示銷售報表")
        print("3. 更新銷售記錄")
        print("4. 刪除銷售記錄")
        print("5. 離開")
        print("**********************************")

        choice = input("請選擇操作項目(Enter 離開)：").strip()
        if not choice:
            break

        if choice == '1':
            sdate = input("請輸入銷售日期 (YYYY-MM-DD)：").strip()
            mid = input("請輸入會員編號：").strip()
            bid = input("請輸入書籍編號：").strip()

            while True:
                try:
                    sqty = int(input("請輸入購買數量：").strip())
                    if sqty <= 0:
                        print("錯誤：數量必須為正整數，請重新輸入")
                        continue
                    break
                except ValueError:
                    print("錯誤：數量必須為整數，請重新輸入")

            while True:
                try:
                    sdiscount = int(input("請輸入折扣金額：").strip())
                    if sdiscount < 0:
                        print("錯誤：折扣金額不能為負數，請重新輸入")
                        continue
                    break
                except ValueError:
                    print("錯誤：折扣金額必須為整數，請重新輸入")

            success, message = add_sale(conn, sdate, mid, bid, sqty, sdiscount)
            print(f"=> {message}")

        elif choice == '2':
            print_sale_report(conn)

        elif choice == '3':
            update_sale(conn)

        elif choice == '4':
            delete_sale(conn)

        elif choice == '5':
            break

        else:
            print("=> 請輸入有效的選項（1-5）")

    conn.close()

if __name__ == "__main__":
    main()