import minqlx_fake


def setup_game_data(
        player_id_map,
        red_team_ids,
        blue_team_ids,
        red_score,
        blue_score,
        aborted=False):
    players_by_teams = {'red': [], 'blue': []}
    for player_id in red_team_ids:
      players_by_teams['red'].append(player_id_map[player_id])
    for player_id in blue_team_ids:
      players_by_teams['blue'].append(player_id_map[player_id])

    minqlx_fake.Plugin.set_game(
        minqlx_fake.Game('ad', red_score, blue_score, aborted))
    minqlx_fake.Plugin.set_players_by_team(players_by_teams)
