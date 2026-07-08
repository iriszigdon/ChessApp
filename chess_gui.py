import tkinter as tk
from tkinter import messagebox, scrolledtext
import socket
import threading
import os
from PIL import Image, ImageTk
from chess_logic import ChessBoard
from network_crypto import NetworkCrypto


class ChessGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CipherVault Chess - 5 Units Project")
        self.board_logic = ChessBoard()
        self.my_color = None
        self.turn = "white"
        self.selected_square = None

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.image_cache = {}

        # יצירת תמונת מפתח של 1x1 פיקסל כדי להכריח גדלי פיקסלים קבועים בלוח
        self.empty_pixel = tk.PhotoImage(width=1, height=1)

        self.setup_ui()
        self.load_piece_images()
        self.update_board_ui()
        self.connect_to_server()

    def setup_ui(self):
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(padx=10, pady=10)

        self.board_frame = tk.Frame(self.main_frame)
        self.board_frame.pack(side=tk.LEFT)

        self.chat_frame = tk.Frame(self.main_frame)
        self.chat_frame.pack(side=tk.RIGHT, padx=20)

        self.buttons = [[None for _ in range(8)] for _ in range(8)]
        for r in range(8):
            for c in range(8):
                color = "#eeeed2" if (r + c) % 2 == 0 else "#769656"

                # יצירת כפתור ריבועי מושלם בגודל 60x60 פיקסלים בעזרת ה-empty_pixel
                btn = tk.Button(self.board_frame, bg=color, relief=tk.FLAT,
                                image=self.empty_pixel, width=60, height=60, compound="center",
                                command=lambda row=r, col=c: self.square_clicked(row, col))
                btn.grid(row=r, column=c)
                self.buttons[r][c] = btn

        self.chat_area = scrolledtext.ScrolledText(self.chat_frame, width=30, height=18, state='disabled')
        self.chat_area.pack()

        self.msg_entry = tk.Entry(self.chat_frame, width=22)
        self.msg_entry.pack(side=tk.LEFT, pady=5)
        self.msg_entry.bind("<Return>", lambda event: self.send_chat())

        self.send_btn = tk.Button(self.chat_frame, text="Send", command=self.send_chat)
        self.send_btn.pack(side=tk.RIGHT, pady=5)

    def load_piece_images(self):
        pieces_names = ["WP", "WR", "WN", "WB", "WQ", "WK", "BP", "BR", "BN", "BB", "BQ", "BK"]
        image_dir = "images"

        if not os.path.exists(image_dir):
            os.makedirs(image_dir)
            return

        for name in pieces_names:
            img_path = os.path.join(image_dir, f"{name}.png")
            if os.path.exists(img_path):
                # התמונות מותאמות בדיוק לגודל הכפתור (55x55 פיקסלים כדי שיישאר שוליים קטנים)
                img = Image.open(img_path).resize((55, 55), Image.Resampling.LANCZOS)
                self.image_cache[name] = ImageTk.PhotoImage(img)

    def update_board_ui(self):
        """מעדכן את הגרפיקה בצורה יציבה שלא מעוותת את הלוח"""
        for r in range(8):
            for c in range(8):
                piece = self.board_logic.grid[r][c]
                if piece:
                    piece_str = str(piece)
                    if piece_str in self.image_cache:
                        # הצבת תמונת הכלי
                        self.buttons[r][c].config(image=self.image_cache[piece_str], text="")
                    else:
                        # גיבוי טקסטואלי אם חסר קובץ
                        self.buttons[r][c].config(text=piece_str, image=self.empty_pixel)
                else:
                    # משבצת ריקה: משתמשים בפיקסל הריק השקוף כדי לשמור על גודל ריבועי מדויק של 60x60
                    self.buttons[r][c].config(image=self.empty_pixel, text="")

    def connect_to_server(self):
        try:
            self.sock.connect(('127.0.0.1', 6666))
            threading.Thread(target=self.listen_to_server, daemon=True).start()
        except:
            messagebox.showerror("Error", "Server is offline!")
            self.root.destroy()

    def listen_to_server(self):
        while True:
            msg = NetworkCrypto.recv_secure_msg(self.sock)
            if not msg:
                break

            parts = msg.split("|")
            cmd = parts[0]

            if cmd == "MATCH_WAIT":
                self.my_color = parts[1]
                self.log_chat(f"System: Waiting for opponent. You are {self.my_color}.")

            elif cmd == "MATCH_START":
                self.my_color = parts[1]
                self.log_chat(f"System: Match started! You are {self.my_color}.")

            elif cmd == "MOVE":
                r1, c1, r2, c2 = map(int, parts[1:])
                self.board_logic.move_piece((r1, c1), (r2, c2))
                self.update_board_ui()
                self.turn = self.my_color

            elif cmd == "CHAT":
                self.log_chat(f"Opponent: {parts[1]}")

            elif cmd == "OPPONENT_DISCONNECTED":
                messagebox.showinfo("Game Over", "Opponent disconnected!")
                break

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
                self.turn = "black" if self.my_color == "white" else "white"
                move_msg = f"MOVE|{start_pos[0]}|{start_pos[1]}|{end_pos[0]}|{end_pos[1]}"
                NetworkCrypto.send_secure_msg(self.sock, move_msg)

    def send_chat(self):
        text = self.msg_entry.get()
        if text:
            self.log_chat(f"You: {text}")
            NetworkCrypto.send_secure_msg(self.sock, f"CHAT|{text}")
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