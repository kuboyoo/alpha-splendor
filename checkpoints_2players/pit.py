#!/usr/bin/env python3

import Arena
from MCTS import MCTS
#from santorini.SantoriniPlayers import *
#from santorini.SantoriniGame import SantoriniGame as Game
#from santorini.NNet import NNetWrapper as NNet

from splendor.SplendorPlayers import *
from splendor.SplendorGame import SplendorGame as Game
from splendor.NNet import NNetWrapper as NNet


import numpy as np
from utils import *
import os.path
from os import stat
import subprocess
import itertools
import json
import multiprocessing
import copy

"""
use this script to play any two agents against each other, or play manually with
any agent.
"""

game = None
_lock = multiprocessing.Lock()

def create_player(name, args):
	global game
	if game is None:
		game = Game()
	# all players
	if name == 'random':
		return RandomPlayer(game).play
	if name == 'greedy':
		return GreedyPlayer(game).play
	if name == 'human':
		return HumanPlayer(game).play
	
	if name == "horizon":
		bias = copy.copy(name)
		name = "./splendor/pretrained_2players.pt"
	else:
		bias = None

	# set default values but will be overloaded when loading checkpoint
	nn_args = dict(lr=None, dropout=0., epochs=None, batch_size=None, nn_version=-1)
	net = NNet(game, nn_args)
	cpt_dir, cpt_file = os.path.split(name)
	additional_keys = net.load_checkpoint(cpt_dir, cpt_file)
	mcts_args = dotdict({
		'numMCTSSims'     : args.numMCTSSims if args.numMCTSSims else additional_keys.get('numMCTSSims', 100),
		'cpuct'           : args.cpuct       if args.cpuct       else additional_keys.get('cpuct'      , 1.0),
		'prob_fullMCTS'   : 1.,
		'forced_playouts' : False,
		'no_mem_optim'    : False,
	})
	mcts = MCTS(game, net, mcts_args)
	player = lambda x: np.argmax(mcts.getActionProb(x, temp=0, force_full_search=True, bias=bias)[0])
	return player

def play(args):
	players = [p+'/best.pt' if os.path.isdir(p) else p for p in args.players]

	print(players[0], 'vs', players[1])
	player1, player2 = create_player(players[0], args), create_player(players[1], args)
	human = 'human' in players
	arena = Arena.Arena(player1, player2, game, display=game.printBoard)
	result = arena.playGames(args.num_games, verbose=args.display or human)
	return result

def play_age(args):
	players = subprocess.check_output(['find', args.compare, '-name', 'best.pt', '-mmin', '-'+str(args.compare_age*60)])
	players = players.decode('utf-8').strip().split('\n')
	print(players)
	list_tasks = list(itertools.combinations(players, 2))
	plays(list_tasks, args)

def plays(list_tasks, args, callback_results=None):
	import math
	import time
	n = len(list_tasks)
	nb_tasks_per_thread = math.ceil(n/args.max_compare_threads)
	nb_threads = math.ceil(n/nb_tasks_per_thread)
	
	current_threads_list = subprocess.check_output(['ps', '-e', '-o', 'cmd'], shell=True).decode('utf-8').split('\n')
	idx_thread = sum([1 for t in current_threads_list if 'pit.py' in t]) - 1
	if idx_thread == 0:
		print(f'\t{n} pits to do, splitted in {nb_tasks_per_thread} tasks * {nb_threads} threads')
	if idx_thread < nb_threads-1:
		print(f'\tPlease call same script {nb_threads-1-idx_thread} time(s) more in other console')
	elif idx_thread >= nb_threads:
		print(f'I already have enough processes, exiting current one')
		exit()
	

	last_kbd_interrupt = 0.
	for (p1, p2) in list_tasks[idx_thread::nb_threads]:
		args.players = [p1, p2]
		try:
			game_results = play(args)

		except KeyboardInterrupt:
			now = time.time()
			if now - last_kbd_interrupt < 10:
				exit(0)
			last_kbd_interrupt = now
			print('Skipping this pit (hit CRTL-C once more to stop all)')
		else:
			if callback_results:
				callback_results(p1, p2, game_results, args)

def load_rating(player_file):
	import glicko2
	basename = os.path.splitext(os.path.basename(player_file))[0]
	rating_file = os.path.dirname(player_file) + '/rating' + ('' if basename == 'best' else '_'+basename) + '.json'
	if not os.path.exists(rating_file):
		return glicko2.Player()
	r_dict = json.load(open(rating_file, 'r'))
	return glicko2.Player(rating=r_dict['rating'], rd=r_dict['rd'], vol=r_dict['vol'])
		

def write_rating(rating_object, player_file):
	basename = os.path.splitext(os.path.basename(player_file))[0]
	rating_file = os.path.dirname(player_file) + '/rating' + ('' if basename == 'best' else '_'+basename) + '.json'
	rating_dict = {'rating': rating_object.rating, 'rd': rating_object.rd, 'vol': rating_object.vol}
	json.dump(rating_dict, open(rating_file, 'w'))

def update_ratings(p1, p2, game_results, args):
	oneWon, twoWon, draws = game_results
	with _lock:
		player1, player2 = load_rating(p1), load_rating(p2)
		p1r, p1rd = player1.rating, player1.rd
		p2r, p2rd = player2.rating, player2.rd
		n = oneWon+twoWon+draws
		player1.update_player([p2r]*n, [p2rd]*n, [1]*oneWon + [0.5]*draws + [0]*twoWon)
		player2.update_player([p1r]*n, [p1rd]*n, [1]*twoWon + [0.5]*draws + [0]*oneWon)
		write_rating(player1, args.players[0])
		write_rating(player2, args.players[1])
		# for p, pname in [(player1, p1), (player2, p2)]:
		# 	print(f'{pname[-20:].rjust(20)} rating={int(p.rating)}±{int(p.rd)}, vol={p.vol:.3e}')

def play_several_files(args):
	players = args.players[:] # Copy, because it will be overwritten by plays()
	list_tasks = []
	if args.reference:
		list_tasks += list(itertools.product(args.players, args.reference))
	if not args.vs_ref_only:
		list_tasks += list(itertools.combinations(args.players, 2))

	if args.ratings:
		plays(list_tasks, args, callback_results=update_ratings)
		for p in players:
			r = load_rating(p)
			name = os.path.basename(os.path.dirname(p)) + ('' if os.path.basename(p) == 'best.pt' else (' - ' + os.path.basename(p)))
			print(f'{name[-20:].ljust(20)} rating={int(r.rating)}±{int(r.rd)}, vol={r.vol:.3e}')
	else:
		plays(list_tasks, args)



def profiling(args):
	import cProfile, pstats

	#args.num_games = 4
	profiler = cProfile.Profile()
	print('\nstart profiling')
	profiler.enable()

	# Core of the training
	print(play(args))

	# debrief
	profiler.disable()
	profiler.dump_stats('execution.prof')
	pstats.Stats(profiler).sort_stats('cumtime').print_stats(20)
	print()
	pstats.Stats(profiler).sort_stats('tottime').print_stats(10)

def main():
	import argparse
	parser = argparse.ArgumentParser(description='tester')  

	parser.add_argument('--num-games'          , '-n' , action='store', default=30   , type=int  , help='')
	parser.add_argument('--profile'                   , action='store_true', help='enable profiling')
	parser.add_argument('--display'                   , action='store_true', help='display')

	parser.add_argument('--numMCTSSims'        , '-m' , action='store', default=None  , type=int  , help='Number of games moves for MCTS to simulate.')
	parser.add_argument('--cpuct'              , '-c' , action='store', default=None  , type=float, help='')

	parser.add_argument('players'                     , metavar='player', nargs='*', help='list of players to test (either file, or "human" or "random")')
	parser.add_argument('--reference'          , '-r' , metavar='ref'   , nargs='*', help='list of reference players')
	parser.add_argument('--vs-ref-only'        , '-z' ,  action='store_true', help='Use this option to prevent games between players, only players vs references')
	parser.add_argument('--ratings'            , '-R' ,  action='store_true', help='Compute ratings based in games results and write ratings on disk')

	parser.add_argument('--compare'            , '-C' , action='store', default='../results', help='Compare all best.pt located in the specified folders')
	parser.add_argument('--compare-age'        , '-A' , action='store', default=None        , help='Maximum age (in hour) of best.pt to be compared', type=int)
	parser.add_argument('--max-compare-threads', '-T' , action='store', default=1           , help='No of threads to run comparison on', type=int)

	args = parser.parse_args()
	
	if args.profile:
		profiling(args)
	elif args.compare_age:
		play_age(args)
	elif args.reference or len(args.players) > 2:
		play_several_files(args)
	elif len(args.players) == 2:
		play(args)
	else:
		raise Exception('Please specify a player (ai folder, random, greedy or human)')

if __name__ == "__main__":
	main()
