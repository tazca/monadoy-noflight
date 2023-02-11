# Originally forked from https://github.com/monadoy/rekry2022-sample

from dotenv import dotenv_values
import requests
import webbrowser
import websocket
import json
from lib.math import normalize_heading
import time

import noflightsolver

FRONTEND_BASE = "noflight.monad.fi"
BACKEND_BASE = "noflight.monad.fi/backend"

game_id = ""
game_solver = noflightsolver.NoflightSolver()

# Example level payload:
# 'game-instance', {'entityId': '01GRGYKJ23X1Y82RRFEZJSMJGG', 'gameState': '{"bbox":[{"x":-180,"y":-180},{"x":180,"y":180}],"aircrafts":[{"id":"1","name":"1","position":{"x":-100,"y":0},"direction":0,"speed":5,"collisionRadius":20,"destination":"A"}],"airports":[{"name":"A","position":{"x":100,"y":0},"direction":0,"landingRadius":10}]}', 'ownerId': '01GRGVHDVB9XJ0J6GX8NY6B20A', 'status': 'ONGOING', 'reason': '', 'createdAt': '2023-02-05T14:10:14.723Z', 'gameType': 'NO_PLANE', 'score': 0, 'levelId': '01GH1E14E88DT3BYWHNYW85ZRV'}]

def on_message(ws: websocket.WebSocketApp, message):
    [action, payload] = json.loads(message)
    print([action, payload])

    if action != "game-instance":
        print([action, payload])
        return

     # New game tick arrived!
    game_state = json.loads(payload["gameState"])

    # NoflightSolver.solve returns required commands for current tick.
    # It doesn't do any actual solving after 1st tick.
    commands = game_solver.solve(game_state)


    print(str(json.dumps(["run-command", {"gameId": game_id, "payload": commands}])))
    time.sleep(0.1)
    ws.send(json.dumps(["run-command", {"gameId": game_id, "payload": commands}]))


def on_error(ws: websocket.WebSocketApp, error):
    print(error)


def on_open(ws: websocket.WebSocketApp):
    print("OPENED")
    ws.send(json.dumps(["sub-game", {"id": game_id}]))


def on_close(ws, close_status_code, close_msg):
    print("CLOSED")


# Change this to your own implementation
def generate_commands(game_state):
    commands = []
#    for aircraft in game_state["aircrafts"]:
        # Go loopy loop
#        new_dir = normalize_heading(aircraft['direction'] + 20)
#        commands.append(f"HEAD {aircraft['id']} {new_dir}")

    return commands


def main():
    config = dotenv_values()
    res = requests.post(
        f"https://{BACKEND_BASE}/api/levels/{config['LEVEL_ID']}",
        headers={
            "Authorization": config["TOKEN"]
        })

    if not res.ok:
        print(f"Couldn't create game: {res.status_code} - {res.text}")
        return

    game_instance = res.json()

    global game_id
    game_id = game_instance["entityId"]

    print(game_id)

    url = f"https://{FRONTEND_BASE}/?id={game_id}"
    print(f"Game at {url}")
    webbrowser.open(url, new=2)
    time.sleep(2)

    ws = websocket.WebSocketApp(
        f"wss://{BACKEND_BASE}/{config['TOKEN']}/", on_message=on_message, on_open=on_open, on_close=on_close, on_error=on_error)
    ws.run_forever()


if __name__ == "__main__":
    main()
