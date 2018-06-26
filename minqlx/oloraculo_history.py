#!/usr/bin/python3.5

import datetime
import json
import os
import trueskill

WORKING_PAHT = '/home/qadmin/steamcmd/steamapps/common/qlds/minqlx-plugins/'
HISTORY_FILE_BASE = os.path.join(WORKING_PAHT, 'oloraculo_history')
OLORACULO_STATS_FILE = os.path.join(WORKING_PAHT, 'oloraculo_stats.json')
GAME_TYPE = 'ad'
FIELDS = ['mu', 'sigma', 'winloss', 'killdeath']

PLAYERS_BY_ID = {
    '76561198014448247': 'BluesyQuaker',
    '76561198261371023': 'CocoCrue',
    '76561198257902041': 'MandioK',
    '76561198282206581': 'Toro',
    '76561198045070268': ']v[ - Fundiar',
    '76561198257667410': 'cfernan77',
    '76561198280762419': 'juanpi.diazv',
    '76561198015775820': 'renga73',
    '76561197969594389': 'goras',
}


def update_history_file(stat, data, player_ids):
  file_name = '%s_%s.tsv' % (HISTORY_FILE_BASE, stat)
  date = datetime.date.isoformat(datetime.date.today())
  history_file = open(file_name, 'a+')
  lines = ['\t'.join([date] + [str(d) for d in data])]
  if os.stat(file_name).st_size == 0:
    header = '\t'.join(['date'] + [PLAYERS_BY_ID[id] for id in player_ids])
    lines = [header] + lines
  history_file.write('\n'.join(lines) + '\n')


stats = json.loads(open(OLORACULO_STATS_FILE).read())[GAME_TYPE]

player_ids = sorted([id for id in PLAYERS_BY_ID.keys() if id in stats])

names = [PLAYERS_BY_ID[id] for id in player_ids]
ratings = [
    trueskill.Rating(stats[id][0], stats[id][1]).exposure for id in player_ids
]
winloss = [stats[id][2] / float(stats[id][3]) for id in player_ids]
killdeath = [stats[id][4] / float(stats[id][5]) for id in player_ids]

update_history_file('ratings', ratings, player_ids)
update_history_file('winloss', winloss, player_ids)
update_history_file('killdeath', killdeath, player_ids)
