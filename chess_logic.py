class Piece:
    def __init__(self, color, name):
        self.color = color  # 'white' או 'black'
        self.name = name  # 'P', 'R', 'N', 'B', 'Q', 'K'

    def is_valid_move(self, start_pos, end_pos, board):
        raise NotImplementedError

    def __str__(self):
        return f"{'W' if self.color == 'white' else 'B'}{self.name}"


class Pawn(Piece):
    def __init__(self, color):
        super().__init__(color, 'P')

    def is_valid_move(self, start_pos, end_pos, board):
        r1, c1 = start_pos
        r2, c2 = end_pos
        direction = -1 if self.color == 'white' else 1
        start_row = 6 if self.color == 'white' else 1

        # תנועה צעד אחד קדימה
        if c1 == c2 and r2 - r1 == direction:
            return board[r2][c2] is None

        # תנועה של שני צעדים מהשורה הראשונה
        if c1 == c2 and r1 == start_row and r2 - r1 == 2 * direction:
            return board[r2][c2] is None and board[r1 + direction][c1] is None

        # אכילה באלכסון
        if abs(c2 - c1) == 1 and r2 - r1 == direction:
            return board[r2][c2] is not None and board[r2][c2].color != self.color

        return False


class Knight(Piece):
    def __init__(self, color):
        super().__init__(color, 'N')

    def is_valid_move(self, start_pos, end_pos, board):
        r1, c1 = start_pos
        r2, c2 = end_pos
        return (abs(r1 - r2), abs(c1 - c2)) in [(2, 1), (1, 2)]


class Rook(Piece):
    def __init__(self, color):
        super().__init__(color, 'R')

    def is_valid_move(self, start_pos, end_pos, board):
        r1, c1 = start_pos
        r2, c2 = end_pos
        if r1 != r2 and c1 != c2:
            return False
        return self._is_path_clear(start_pos, end_pos, board)

    def _is_path_clear(self, start, end, board):
        r1, c1 = start
        r2, c2 = end
        dr = max(-1, min(1, r2 - r1))
        dc = max(-1, min(1, c2 - c1))
        curr_r, curr_c = r1 + dr, c1 + dc
        while (curr_r, curr_c) != (r2, c2):
            if board[curr_r][curr_c] is not None:
                return False
            curr_r += dr
            curr_c += dc
        return True


class Bishop(Piece):
    def __init__(self, color):
        super().__init__(color, 'B')

    def is_valid_move(self, start_pos, end_pos, board):
        r1, c1 = start_pos
        r2, c2 = end_pos
        if abs(r1 - r2) != abs(c1 - c2):
            return False

        dr = max(-1, min(1, r2 - r1))
        dc = max(-1, min(1, c2 - c1))
        curr_r, curr_c = r1 + dr, c1 + dc
        while (curr_r, curr_c) != (r2, c2):
            if board[curr_r][curr_c] is not None:
                return False
            curr_r += dr
            curr_c += dc
        return True


class Queen(Piece):
    def __init__(self, color):
        super().__init__(color, 'Q')

    def is_valid_move(self, start_pos, end_pos, board):
        r1, c1 = start_pos
        r2, c2 = end_pos
        if r1 == r2 or c1 == c2:
            return Rook(self.color).is_valid_move(start_pos, end_pos, board)
        if abs(r1 - r2) == abs(c1 - c2):
            return Bishop(self.color).is_valid_move(start_pos, end_pos, board)
        return False


class King(Piece):
    def __init__(self, color):
        super().__init__(color, 'K')

    def is_valid_move(self, start_pos, end_pos, board):
        r1, c1 = start_pos
        r2, c2 = end_pos
        return abs(r1 - r2) <= 1 and abs(c1 - c2) <= 1


class ChessBoard:
    def __init__(self):
        self.grid = [[None for _ in range(8)] for _ in range(8)]
        self.setup_board()

    def setup_board(self):
        order = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]
        for c in range(8):
            self.grid[0][c] = order[c]('black')
            self.grid[1][c] = Pawn('black')
            self.grid[6][c] = Pawn('white')
            self.grid[7][c] = order[c]('white')

    def move_piece(self, start_pos, end_pos):
        r1, c1 = start_pos
        r2, c2 = end_pos
        piece = self.grid[r1][c1]

        if piece and piece.is_valid_move(start_pos, end_pos, self.grid):
            target = self.grid[r2][c2]
            if target and target.color == piece.color:
                return False
            self.grid[r2][c2] = piece
            self.grid[r1][c1] = None
            return True
        return False