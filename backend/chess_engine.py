import chess


class ChessEngine:
    def __init__(self, fen=None):
        self.board = chess.Board(fen) if fen else chess.Board()

    def play_move(self, move_uci: str):
        try:
            move = chess.Move.from_uci(move_uci)

            if move not in self.board.legal_moves:
                return {
                    "valid": False,
                    "message": "Illegal move"
                }

            self.board.push(move)

            return {
                "valid": True,
                "fen": self.board.fen(),
                "turn": "white" if self.board.turn else "black",
                "check": self.board.is_check(),
                "checkmate": self.board.is_checkmate(),
                "stalemate": self.board.is_stalemate(),
                "game_over": self.board.is_game_over()
            }

        except Exception as e:
            return {
                "valid": False,
                "message": str(e)
            }