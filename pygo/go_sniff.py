
from ast import parse
import pyperclip, json
import string
from typing import Union
class Game():
    def __init__(self,data:Union[dict,str]) -> None:
        if isinstance(data,dict):
            self.is_json = True
        else:
            self.is_json = False
        self.data = data
        self.moves = data['gamedata']['moves']
    def add_metadata(self):
        metadata = {
            'GM':1,
            'SZ':self.data['gamedata']['width'],
            'KM':self.data['gamedata']['komi']
        }
        return [f"{key}[{val}]" for key,val in metadata.items()]
    def add_moves(self):
        rc = list(string.ascii_lowercase)
        val = []
        for i,m in enumerate(self.moves):
            player = "B"
            if i % 2 != 0:
                player = "W"
            val.append(f";{player}[{rc[m[0]]}{rc[m[1]]}]")

        return val

    def to_sgf(self):
        game = ['(;'] + self.add_metadata() + self.add_moves() + [')']
        return '\n'.join(game)



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Copy OGS game data to')
    parser.add_argument('input',nargs="?",type=str, help='Input Link',default='https://online-go.com/game/40476992')
    args = parser.parse_args()

    print(args.input)

    game_id = args.input.split("/")[-1]
    api_url = "https://online-go.com/api/v1/games/"+game_id
    print(api_url)

    import requests

    f = requests.get(api_url)
    d = json.loads(f.text)

    game = Game(d)
    sgf = game.to_sgf()
    print(sgf)
    pyperclip.copy(sgf)