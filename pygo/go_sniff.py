from ast import parse
import copy
import pyperclip, json
import string
from typing import Union
import numpy as np

def split_each_n_characters(string,n=2):
    return [string[i:i+n] for i in range(0, len(string), n)]

class Player:
    def __init__(self, data: Union[dict, str], color: str = None) -> None:
        self.ID = data["id"]
        self.name = data["username"]
        self.color = color

    def to_sgf(self):
        if self.color == "black":
            return "B"
        else:
            return "W"


class Game:
    def __init__(self, data: Union[dict, str], analysis=True) -> None:
        if isinstance(data, dict):
            self.is_json = True
        else:
            self.is_json = False
        self.data = data
        self.analysis = analysis
        self.moves = data["gamedata"]["moves"]
        self.initial_player = data["gamedata"]["initial_player"]
        self.second_player = 'white' if self.initial_player == 'black' else 'black'
        self.players = {c:Player(data=data["players"][c], color=c) for c in ['black','white']}

    def add_metadata(self) -> list:
        metadata = {"GM": 1, "SZ": self.data["gamedata"]["width"], "KM": self.data["gamedata"]["komi"]}
        return [f"{key}[{val}]" for key, val in metadata.items()]
    
    def add_initial(self) -> list:
        moves = []
        if "initial_state" in self.data['gamedata']:
            for player in ['black','white']:
                player_moves = split_each_n_characters(self.data['gamedata']['initial_state'][player])
                for m in player_moves:
                    moves.append(f"A{self.players[player].to_sgf()}[{m}]")
        return moves




    def add_moves(self) -> list:
        rc = list(string.ascii_lowercase)

        ogs_rows = np.arange(1,20)
        ogs_rows = ogs_rows[np.argsort(-ogs_rows)]
        ogs_cols = copy.deepcopy(rc)
        ogs_cols.remove("i")

        val = []        
        for i, m in enumerate(self.moves):
            move_coordinates = [ogs_cols[m[0]],ogs_rows[m[1]]]

            # print(f"{i}:{move_coordinates}")
            player = self.players[self.initial_player]
            if i%2 != 0:
                player = self.players[self.second_player]
            # Perform some analysis on moves

            

            if self.analysis:
                if isinstance(m[-1], dict):
                    d = m[-1]  # shortcut
                    if "blur" in d:
                        print(f'> Move number {i}: {move_coordinates} played by {player.name} is "blur", careful')
                    sgf_downloaded_by = d.get("sgf_downloaded_by", [])
                    if len(sgf_downloaded_by) > 0:
                        print(f"> {player.name} Game downloaded on move number {i} : {move_coordinates}")


            val.append(f";{player.to_sgf()}[{rc[m[0]]}{rc[m[1]]}]")

        return val

    def to_sgf(self) -> str:
        game = ["(;"] + self.add_metadata() + self.add_initial() + self.add_moves() + [")"]
        return "\n".join(game)

    def __str__(self) -> str:
        return json.dumps(self.data, indent=2)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Copy OGS game data to")
    parser.add_argument("input", nargs="?", type=str, help="Input Link", default="https://online-go.com/game/40476992")
    args = parser.parse_args()

    print(args.input)

    game_id = args.input.split("/")[-1]
    api_url ='%s/%s' % ("https://online-go.com/api/v1/games", game_id)
    
    print(api_url)

    import requests

    f = requests.get(api_url)
    
    d = json.loads(f.text)
    game = Game(d)
    sgf = game.to_sgf()

    pyperclip.copy(sgf)


if __name__ == "__main__":
    main()
