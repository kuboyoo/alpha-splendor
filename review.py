import numpy as np
import os

from MCTS import MCTS
from splendor.SplendorGame import SplendorGame as Game
from splendor.NNet import NNetWrapper as NNet
from utils import *
from pathlib import Path
import argparse

def review(canonical_board, game, curPlayer, model_name, num_mcts, temp=0):
  nn_args = dict(lr=None, dropout=0., epochs=None, batch_size=None, nn_version=-1)
  net = NNet(game, nn_args)
  cpt_dir, cpt_file = os.path.split(model_name)
  additional_keys = net.load_checkpoint(cpt_dir, cpt_file)
  cpuct = None
  mcts_args = dotdict({
    'numMCTSSims'     : num_mcts, # if args.numMCTSSims else additional_keys.get('numMCTSSims', 100),
    'cpuct'           : cpuct       if cpuct       else additional_keys.get('cpuct'      , 1.0),
    'prob_fullMCTS'   : 1.,
    'forced_playouts' : False,
    'no_mem_optim'    : False,
  })
  mcts = MCTS(game, net, mcts_args)

  prob = mcts.getActionProb(canonical_board, temp=temp, force_full_search=True, bias=None)[0]
  prob = np.array(prob)
  idx = np.argsort(prob)[::-1][:5] #AI行動確率>0の上位5候補手

  print("AI Suggest:")
  for i, p in zip(idx, prob[idx]):
      print("[%d]: %2.1f%%: %s" % (i, p*100, game.moveToString(i, curPlayer)))


def main(turn_num):
  record_dir = Path("./record/220212_02/")

  board_path = record_dir.joinpath("board_turn_%d.pkl" % (turn_num+1))
  #canon_path = record_dir.joinpath("cannonical_board_turn_%d.pkl" % (turn_num+1))

  board = loadPkl(board_path)
  #canonical_board = loadPkl(canon_path)
  num_players = 3
  curPlayer = turn_num % num_players
  model_name = "./splendor/pretrained_%dplayers.pt" % num_players
  game = Game(num_players)

  game.printBoard(board)
  print(f"Player {curPlayer} 's. turn ...")

  for n in [100, 1000, 1600, 3000, 10000, 100000, 500000]:
    print("Num of MCTS: ", n)
    review(board, game, curPlayer, model_name, num_mcts=n, temp=1)
  
  

if __name__ == "__main__":
  parser = argparse.ArgumentParser(description='tester')
  parser.add_argument('--turn-num', '-n' , action='store', default=0, type=int, help='review target number(1-)')
  args = parser.parse_args()
  main(args.turn_num)