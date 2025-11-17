import sqlite3
from tabulate import tabulate

DB_PATH = r"D:\Codes\SecureVault\vault.db"

def main():
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, original_name, encrypted_name, timestamp FROM vault_files")
        rows = cur.fetchall()

        if not rows:
            print("No records found in the vault database.")
            return

        headers = ["ID", "Original File", "Encrypted File", "Timestamp"]
        print(tabulate(rows, headers=headers, tablefmt="grid"))

    except FileNotFoundError:
        print(f"Database not found at {DB_PATH}")
    except Exception as e:
        print("Error:", e)
    finally:
        try:
            conn.close()
        except:
            pass

if __name__ == "__main__":
    main()
