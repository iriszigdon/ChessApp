import socket
import threading
from network_crypto import NetworkCrypto


class ChessServer:
    def __init__(self, host='127.0.0.1', port=6666):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen(4)
        self.waiting_client = None  # ממתין לשחקן שני
        print("[*] Chess Server is up and running...")

    def start(self):
        while True:
            client_sock, addr = self.server.accept()
            print(f"[+] Player connected from {addr}")

            if self.waiting_client is None:
                self.waiting_client = client_sock
                NetworkCrypto.send_secure_msg(client_sock, "MATCH_WAIT|white")
            else:
                player1 = self.waiting_client
                player2 = client_sock
                self.waiting_client = None

                NetworkCrypto.send_secure_msg(player2, "MATCH_START|black")
                NetworkCrypto.send_secure_msg(player1, "MATCH_START|white")

                # הקמת Threads לניהול זוג השחקנים במקביל
                threading.Thread(target=self.handle_match, args=(player1, player2), daemon=True).start()
                threading.Thread(target=self.handle_match, args=(player2, player1), daemon=True).start()

    def handle_match(self, current_player, opponent):
        try:
            while True:
                msg = NetworkCrypto.recv_secure_msg(current_player)
                if not msg:
                    break

                # השרת מנתב את ההודעה (מהלך או צ'אט) ישירות ליריב
                print(f"[Match Data]: {msg}")
                NetworkCrypto.send_secure_msg(opponent, msg)
        except:
            pass
        finally:
            try:
                NetworkCrypto.send_secure_msg(opponent, "OPPONENT_DISCONNECTED")
                current_player.close()
                opponent.close()
            except:
                pass


if __name__ == "__main__":
    server = ChessServer()
    server.start()