import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog
import socket
import threading
import os
from PIL import Image, ImageTk
from chess_logic import ChessBoard
from network_crypto import NetworkCrypto


class ChessGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CipherVault Advanced Chess")
        self.root.geometry("400x500")  # גודל התחלתי למסך לוגאין

        self.board_logic = None
        self.my_color = None
        self.turn = None
        self.selected_square = None
        self.game_id = None
        self.my_username = None
        self.opponent_username = None

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.image_cache = {}
        self.empty_pixel = tk.PhotoImage(width=1, height=1)

        # מסגרת על (Container) שמחזיקה את המסכים
        self.container = tk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        self.frames = {}

        # חיבור ראשוני לשרת
        self.connect_to_server()

        # בניית מסכי הממשק
        self.create_auth_frame()
        self.show_frame("auth")

    def connect_to_server(self):
        try:
            self.sock.connect(('127.0.0.1', 6666))
            threading.Thread(target=self.listen_to_server, daemon=True).start()
        except:
            messagebox.showerror("Error", "Server is offline!")
            self.root.destroy()

    def show_frame(self, name):
        """מציגה מסך ספציפי ומסתירה את השאר"""
        for f in self.frames.values():
            f.pack_forget()
        self.frames[name].pack(fill="both", expand=True)

    # ==========================================
    # 1. מסך התחברות והרשמה (Auth Frame)
    # ==========================================
    def create_auth_frame(self):
        frame = tk.Frame(self.container, bg="#2c3e50")
        self.frames["auth"] = frame

        tk.Label(frame, text="CipherVault Chess Login", fg="white", bg="#2c3e50", font=("Arial", 16, "bold")).pack(
            pady=20)

        tk.Label(frame, text="Username:", fg="white", bg="#2c3e50").pack(pady=5)
        self.user_entry = tk.Entry(frame, width=25)
        self.user_entry.pack()

        tk.Label(frame, text="Password:", fg="white", bg="#2c3e50").pack(pady=5)
        self.pass_entry = tk.Entry(frame, width=25, show="*")
        self.pass_entry.pack()

        tk.Button(frame, text="Login", width=15, bg="#3498db", fg="white", command=self.handle_login).pack(pady=15)
        tk.Button(frame, text="Register New Account", width=18, bg="#2ecc71", fg="white",
                  command=self.handle_register).pack(pady=5)

    def handle_login(self):
        user = self.user_entry.get()
        passw = self.pass_entry.get()
        if user and passw:
            self.my_username = user
            NetworkCrypto.send_secure_msg(self.sock, f"LOGIN|{user}|{passw}")
        else:
            messagebox.showwarning("Input Error", "Please fill all fields.")

    def handle_register(self):
        user = self.user_entry.get()
        passw = self.pass_entry.get()
        if user and passw:
            NetworkCrypto.send_secure_msg(self.sock, f"REGISTER|{user}|{passw}")
        else:
            messagebox.showwarning("Input Error", "Please fill all fields.")

    # ==========================================
    # 2. מסך לובי המשתמשים (Lobby Frame)
    # ==========================================
    def create_lobby_frame(self):
        frame = tk.Frame(self.container, bg="#34495e")
        self.frames["lobby"] = frame

        tk.Label(frame, text=f"Welcome, {self.my_username}!", fg="white", bg="#34495e", font=("Arial", 14)).pack(
            pady=10)
        tk.Label(frame, text="Online Players:", fg="white", bg="#34495e").pack()

        # רשימת המשתמשים הויזואלית
        self.user_listbox = tk.Listbox(frame, width=30, height=12)
        self.user_listbox.pack(pady=10)

        tk.Button(frame, text="Challenge Player", bg="#e67e22", fg="white", font=("Arial", 11, "bold"),
                  command=self.send_challenge).pack(pady=10)

    def send_challenge(self):
        try:
            selected_user = self.user_listbox.get(self.user_listbox.curselection())
            if selected_user == self.my_username:
                messagebox.showwarning("Error", "You cannot challenge yourself!")
                return
            NetworkCrypto.send_secure_msg(self.sock, f"CHALLENGE|{selected_user}")
            messagebox.showinfo("Challenge Sent", f"Invitation sent to {selected_user}. Waiting for response...")
        except:
            messagebox.showwarning("Selection Error", "Please select a player from the list.")

    # ==========================================
    # 3. מסך המשחק הראשי (Game Frame)
    # ==========================================
    def create_game_frame(self):
        frame = tk.Frame(self.container)
        self.frames["game"] = frame

        self.board_frame = tk.Frame(frame)
        self.board_frame.pack(side=tk.LEFT, padx=10, pady=10)

        self.chat_frame = tk.Frame(frame)
        self.chat_frame.pack(side=tk.RIGHT, padx=10, pady=10)

        # בניית הלוח הגרפי
        self.buttons = [[None for _ in range(8)] for _ in range(8)]
        for r in range(8):
            for c in range(8):
                color = "#eeeed2" if (r + c) % 2 == 0 else "#769656"
                btn = tk.Button(self.board_frame, bg=color, relief=tk.FLAT,
                                image=self.empty_pixel, width=60, height=60, compound="center",
                                command=lambda row=r, col=c: self.square_clicked(row, col))
                btn.grid(row=r, column=c)
                self.buttons[r][c] = btn

        # צ'אט המשחק
        self.chat_area = scrolledtext.ScrolledText(self.chat_frame, width=25, height=18, state='disabled')
        self.chat_area.pack()

        self.msg_entry = tk.Entry(self.chat_frame, width=18)
        self.msg_entry.pack(side=tk.LEFT, pady=5)
        self.msg_entry.bind("<Return>", lambda event: self.send_chat())

        tk.Button(self.chat_frame, text="Send", command=self.send_chat).pack(side=tk.RIGHT, pady=5)

        self.load_piece_images()

    def load_piece_images(self):
        pieces_names = ["WP", "WR", "WN", "WB", "WQ", "WK", "BP", "BR", "BN", "BB", "BQ", "BK"]
        image_dir = "images"
        for name in pieces_names:
            img_path = os.path.join(image_dir, f"{name}.png")
            if os.path.exists(img_path):
                img = Image.open(img_path).resize((55, 55), Image.Resampling.LANCZOS)
                self.image_cache[name] = ImageTk.PhotoImage(img)

    def update_board_ui(self):
        for r in range(8):
            for c in range(8):
                piece = self.board_logic.grid[r][c]
                if piece:
                    piece_str = str(piece)
                    if piece_str in self.image_cache:
                        self.buttons[r][c].config(image=self.image_cache[piece_str], text="")
                    else:
                        self.buttons[r][c].config(text=piece_str, image=self.empty_pixel)
                else:
                    self.buttons[r][c].config(image=self.empty_pixel, text="")

    # ==========================================
    # מנגנון קבלת מסרים מהשרת (האזנה ברקע)
    # ==========================================
    def listen_to_server(self):
        while True:
            msg = NetworkCrypto.recv_secure_msg(self.sock)
            if not msg:
                break

            parts = msg.split("|")
            cmd = parts[0]

            # תגובות מערכת זיהוי ורישום
            if cmd == "REGISTER_SUCCESS":
                messagebox.showinfo("Success", "Account created successfully! You can now login.")
            elif cmd == "REGISTER_FAIL":
                messagebox.showerror("Failed", parts[1])
            elif cmd == "LOGIN_SUCCESS":
                # מעבר חלק למסך הלובי
                self.root.geometry("350x450")
                self.create_lobby_frame()
                self.show_frame("lobby")
            elif cmd == "LOGIN_FAIL":
                messagebox.showerror("Login Failed", parts[1])

            # עדכון רשימת משתמשים בלובי
            elif cmd == "USER_LIST":
                if "lobby" in self.frames:
                    self.user_listbox.delete(0, tk.END)
                    for user in parts[1].split(","):
                        if user:
                            self.user_listbox.insert(tk.END, user)

            # קבלת הזמנה למשחק
            elif cmd == "CHALLENGE":
                challenger = parts[1]
                ans = messagebox.askyesno("Game Invitation",
                                          f"Player '{challenger}' wants to play chess with you. Accept?")
                if ans:
                    NetworkCrypto.send_secure_msg(self.sock, f"CHALLENGE_ACCEPT|{challenger}")
                else:
                    NetworkCrypto.send_secure_msg(self.sock, f"CHALLENGE_DECLINE|{challenger}")

            elif cmd == "CHALLENGE_DECLINED":
                messagebox.showinfo("Declined", f"Player {parts[1]} declined your challenge.")

            # הזמנה התקבלה - תחילת המשחק!
            elif cmd == "GAME_START":
                self.game_id = int(parts[1])
                self.my_color = parts[2]
                self.opponent_username = parts[3]
                self.turn = "white"
                self.board_logic = ChessBoard()

                # הרחבת החלון עבור לוח המשחק
                self.root.geometry("800x550")
                self.create_game_frame()
                self.update_board_ui()
                self.show_frame("game")
                self.log_chat(f"System: Match started against {self.opponent_username}! You are {self.my_color}.")

            # קבלת מהלך ברשת במשחק הנוכחי
            elif cmd == "MOVE":
                g_id = int(parts[1])
                if g_id == self.game_id:
                    r1, c1, r2, c2 = map(int, parts[2:])
                    self.board_logic.move_piece((r1, c1), (r2, c2))
                    self.update_board_ui()

                    winner = self.board_logic.check_winner()
                    if winner:
                        messagebox.showinfo("Game Over", f"Game Over! The {winner} player has won.")
                        self.turn = None
                    else:
                        self.turn = self.my_color

            # קבלת הודעת צ'אט במשחק
            elif cmd == "CHAT":
                g_id = int(parts[1])
                if g_id == self.game_id:
                    self.log_chat(f"{self.opponent_username}: {parts[2]}")

    # ==========================================
    # פונקציות לחיצה ותנועה על הלוח
    # ==========================================
    def square_clicked(self, r, c):
        if self.turn != self.my_color:
            return

        if self.selected_square is None:
            piece = self.board_logic.grid[r][c]
            if piece and piece.color == self.my_color:
                self.selected_square = (r, c)
                self.buttons[r][c].config(bg="yellow")
        else:
            start_pos = self.selected_square
            end_pos = (r, c)

            orig_color = "#eeeed2" if (start_pos[0] + start_pos[1]) % 2 == 0 else "#769656"
            self.buttons[start_pos[0]][start_pos[1]].config(bg=orig_color)
            self.selected_square = None

            if self.board_logic.move_piece(start_pos, end_pos):
                self.update_board_ui()

                winner = self.board_logic.check_winner()
                if winner:
                    messagebox.showinfo("Game Over", f"Victory! You have won the match!")
                    self.turn = None
                else:
                    self.turn = "black" if self.my_color == "white" else "white"

                # מבנה שליחת מהלך מעודכן הכולל את מזהה המשחק הנוכחי
                move_msg = f"MOVE|{self.game_id}|{start_pos[0]}|{start_pos[1]}|{end_pos[0]}|{end_pos[1]}"
                NetworkCrypto.send_secure_msg(self.sock, move_msg)

    def send_chat(self):
        text = self.msg_entry.get()
        if text:
            self.log_chat(f"You: {text}")
            NetworkCrypto.send_secure_msg(self.sock, f"CHAT|{self.game_id}|{text}")
            self.msg_entry.delete(0, tk.END)

    def log_chat(self, msg_str):
        self.chat_area.config(state='normal')
        self.chat_area.insert(tk.END, msg_str + "\n")
        self.chat_area.config(state='disabled')
        self.chat_area.see(tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = ChessGUI(root)
    root.mainloop()