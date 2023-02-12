import numpy as np
import random

from .SplendorLogic import print_board, move_to_str

class RandomPlayer():
	def __init__(self, game):
		self.game = game

	def play(self, board, player=0):
		valids = self.game.getValidMoves(board, player)
		action = random.choices(range(self.game.getActionSize()), weights=valids.astype(np.int), k=1)[0]
		return action
"""
class StrategicPlayer():
	def __init__(self, game, params):
		self.game = game
		self.params = params

	def play(self, board):
"""

"""
class ValueFunctionPlayer():
	TRANSLATE_VARIETY = 4
	
	DEFAULT_WEIGHTS = {

	}

	CONTENDER_WEIGHTS = {

	}

	def __init__(self, game, params=None, value_fn_builder_name=None):
		self.game = game
		self.params = params

	def base_fn(params=DEFAULT_WEIGHTS):
		def fn(game):

	def contender_fn(params):
    return base_fn(params or CONTENDER_WEIGHTS)
	
	def get_value_fn(name, params, value_function=None):
		if value_function is not None:
			return value_function
		elif name == "base_fn":
      return base_fn(DEFAULT_WEIGHTS)
		elif name == "contender_fn":
			return contender_fn(params)
		else:
      raise ValueError

	def play(self, board, player=0):
	

		
"""

class HumanPlayer():
	def __init__(self, game):
		self.game = game

	def show_all_moves(self, valid):
		for i, v in enumerate(valid):
			if i in [12,12+15,12+15+3+30]:
				print()
			if v:
				print(f'{i} = {move_to_str(i, short=True)}', end='   ')
		print()

	def show_main_moves(self, valid):
		# Number of max gems that player can take
		if any(valid[45:55]):
			can_take = 3
		elif any(valid[35:45]):
			can_take = 2
		elif any(valid[30:35]):
			can_take = 1
		else:
			can_take = 0
		need_to_give_gems = (self.game.board.players_gems[0].sum() >= 9)

		print()
		if any(valid[12:27]):
			print(f'12-26 = rsv', end='   ')
		for i, v in enumerate(valid):
			if v:
				if 0<=i<12 or 27<=i<30 or (30<=i<35 and can_take<=1) or (35<=i<45 and can_take<=2) or 45<=i<60 or (60<=i<80 and need_to_give_gems):
					print(f'{i} = {move_to_str(i, short=True)}', end='   ')		
		print('(+ to show all moves)')

	def play(self, board):
		# print_board(self.game.board)
		valid = self.game.getValidMoves(board, 0)
		self.show_main_moves(valid)
		while True:
			input_move = input()
			if input_move == '+':
				self.show_all_moves(valid)
			else:
				try:
					a = int(input_move)
					if not valid[a]:
						raise Exception('')
					break
				except:
					print('Invalid move:', input_move)
		return a


class GreedyPlayer():
	def __init__(self, game):
		self.game = game

	def play(self, board):
		valids = self.game.getValidMoves(board, 0)
		candidates = []
		initial_score = self.game.getScore(board, 0)
		for m in [m_ for m_, v in enumerate(valids) if v>0]:
			nextBoard, _ = self.game.getNextState(board, 0, m)
			score = self.game.getScore(nextBoard, 1)
			candidates += [(score, m)]
		max_score = max(candidates, key=lambda x: x[0])[0]
		if max_score == initial_score:
			actions_leading_to_max = [m for (m, v) in enumerate(valids) if v>0 and 0      <=m<12        ]
			if len(actions_leading_to_max) == 0:
				actions_leading_to_max = [m for (m, v) in enumerate(valids) if v>0 and 12+15+3<=m<12+15+3+30]
				if len(actions_leading_to_max) == 0:
					actions_leading_to_max = [m for (m, v) in enumerate(valids) if v>0]
		else:
			actions_leading_to_max = [m for (s,m) in candidates if s==max_score]
		move = random.choice(actions_leading_to_max)
		return move