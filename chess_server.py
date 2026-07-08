import socket
import threading
import sqlite3
import hashlib
from network_crypto import NetworkCrypto

DB_NAME = "users.db"


def init_db():
    """יצירת טבלת המשתמשים במידה ולא קיימת"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


class ChessServer:
    def __init__(self, host='127.0.0.1', port=6666):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen(10)

        # ניהול מחוברים: { username: socket }
        self.connected_clients = {}
        self.clients_lock = threading.Lock()

        # ניהול משחקים פעילים: { game_id: (white_sock, black_sock) }
        self.active_games = {}
        self.game_counter = 0

        print("[*] Advanced Chess Server with DB is running...")

    def start(self):
        init_db()
        while True:
            client_sock, addr = self.server.accept()
            print(f"[+] New connection from {addr}")
            # כל לקוח שמציף חיבור מקבל ת'רד משלו בשלב הלוגאין
            threading.Thread(target=self.auth_handler, args=(client_sock,), daemon=True).start()

    def hash_password(self, password):
        """הצפנת סיסמה ב-SHA256 (חובה להגנת סייבר בפרויקט!)"""
        return hashlib.sha256(password.encode()).hexdigest()

    def auth_handler(self, sock):
        """מטפל בלקוח בשלב ההתחברות וההרשמה"""
        username = None
        try:
            while True:
                msg = NetworkCrypto.recv_secure_msg(sock)
                if not msg:
                    break

                parts = msg.split("|")
                cmd = parts[0]

                if cmd == "REGISTER":
                    user, pswd = parts[1], parts[2]
                    success = self.register_user(user, pswd)
                    if success:
                        NetworkCrypto.send_secure_msg(sock, "REGISTER_SUCCESS")
                    else:
                        NetworkCrypto.send_secure_msg(sock, "REGISTER_FAIL|Username already taken!")

                elif cmd == "LOGIN":
                    user, pswd = parts[1], parts[2]
                    with self.clients_lock:
                        already_logged = user in self.connected_clients

                    if already_logged:
                        NetworkCrypto.send_secure_msg(sock, "LOGIN_FAIL|User already logged in from another device!")
                    elif self.validate_login(user, pswd):
                        username = user
                        with self.clients_lock:
                            self.connected_clients[username] = sock
                        NetworkCrypto.send_secure_msg(sock, "LOGIN_SUCCESS")
                        print(f"[+ ] {username} has successfully logged in.")
                        self.broadcast_user_list()
                        # עוברים ללולאת המשחק הראשית של הלקוח המחובר
                        self.main_client_loop(username, sock)
                        break
                    else:
                        NetworkCrypto.send_secure_msg(sock, "LOGIN_FAIL|Invalid username or password.")
        except Exception as e:
            print(f"[-] Error in auth: {e}")
        finally:
            if not username:
                sock.close()

    def register_user(self, username, password):
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            hashed = self.hash_password(password)
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # שם המשתמש תפוס
        finally:
            conn.close()

    def validate_login(self, username, password):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        hashed = self.hash_password(password)
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed))
        user = cursor.fetchone()
        conn.close()
        return user is not None

    def broadcast_user_list(self):
        """שולח לכולם את רשימת המשתמשים המחוברים כרגע"""
        with self.clients_lock:
            users = list(self.connected_clients.keys())
        users_str = ",".join(users)

        with self.clients_lock:
            for sock in self.connected_clients.values():
                try:
                    NetworkCrypto.send_secure_msg(sock, f"USER_LIST|{users_str}")
                except:
                    pass

    def main_client_loop(self, username, sock):
        """לולאת המסרים הראשית לאחר שהמשתמש מחובר למערכת"""
        try:
            while True:
                msg = NetworkCrypto.recv_secure_msg(sock)
                if not msg:
                    break

                parts = msg.split("|")
                cmd = parts[0]

                if cmd == "GET_USERS":
                    self.broadcast_user_list()

                elif cmd == "CHALLENGE":
                    target_user = parts[1]
                    with self.clients_lock:
                        target_sock = self.connected_clients.get(target_user)
                    if target_sock:
                        NetworkCrypto.send_secure_msg(target_sock, f"CHALLENGE|{username}")

                elif cmd == "CHALLENGE_ACCEPT":
                    challenger = parts[1]
                    with self.clients_lock:
                        challenger_sock = self.connected_clients.get(challenger)

                    if challenger_sock:
                        self.game_counter += 1
                        g_id = self.game_counter
                        # שמירת המשחק הפעיל במערכת
                        self.active_games[g_id] = (challenger_sock, sock)

                        # שליחת אישור תחילת משחק לשניהם עם הגדרת מזהה משחק וצבעים
                        NetworkCrypto.send_secure_msg(challenger_sock, f"GAME_START|{g_id}|white|{username}")
                        NetworkCrypto.send_secure_msg(sock, f"GAME_START|{g_id}|black|{challenger}")

                elif cmd == "CHALLENGE_DECLINE":
                    challenger = parts[1]
                    with self.clients_lock:
                        challenger_sock = self.connected_clients.get(challenger)
                    if challenger_sock:
                        NetworkCrypto.send_secure_msg(challenger_sock, f"CHALLENGE_DECLINED|{username}")

                elif cmd == "MOVE":
                    # מבנה מהלך חדש: MOVE|game_id|r1|c1|r2|c2
                    g_id = int(parts[1])
                    if g_id in self.active_games:
                        p1, p2 = self.active_games[g_id]
                        # העברת המסר לשחקן השני (מזהים מי שלח ומעבירים לאחר)
                        target_sock = p2 if sock == p1 else p1
                        try:
                            NetworkCrypto.send_secure_msg(target_sock, msg)
                        except:
                            pass

                elif cmd == "CHAT":
                    # מבנה צ'אט חדש: CHAT|game_id|text
                    g_id = int(parts[1])
                    if g_id in self.active_games:
                        p1, p2 = self.active_games[g_id]
                        target_sock = p2 if sock == p1 else p1
                        try:
                            NetworkCrypto.send_secure_msg(target_sock, msg)
                        except:
                            pass
        except:
            pass
        finally:
            # ניקוי משתמש שהתנתק
            with self.clients_lock:
                if username in self.connected_clients:
                    del self.connected_clients[username]
            print(f"[-] {username} disconnected.")
            sock.close()
            self.broadcast_user_list()


if __name__ == "__main__":
    server = ChessServer()
    server.start()