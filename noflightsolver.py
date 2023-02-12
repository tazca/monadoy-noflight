from math import ceil, floor
from typing import Optional, Tuple

# debugging
import json

from lib.math import angular_difference, calculate_direction, calculate_length, normalize_heading, \
    right_or_left, turn_circle_xy, find_tangent_points, select_ideal_tangent_point

class NoflightSolver:

    TURN_R: float = 14.18

    def __init__(self):
        self.commands_list = []
        self.commands_per_tick = [] # cleaned up commands for consumption
        pass

    def solve(self, game_state):
        # let's assume that the solution will not require compensation for model-reality drift and solve
        # only once when starting
        if (self.commands_list == []):
            aircrafts = game_state["aircrafts"]
            airports = game_state["airports"]

            for ac in aircrafts:
                for ap in airports:
                    if ac["destination"] == ap["name"]:
                        path = self._make_optimal_route(
                            (ac["position"]["x"], ac["position"]["y"]),
                            ac["direction"],
                            (ap["position"]["x"], ap["position"]["y"]),
                            ap["direction"]
                        )
                        self.commands_list.append(
                            (ac["id"], path)
                        )

            for ac in self.commands_list:
                self._map_commands_against_ticks(ac)

        # return next tick's commands
        return self.commands_per_tick.pop(0)

    def _map_commands_against_ticks(self,
                                    cmds_list: Tuple[str, list[int]]
                                    ):
        (ac_id, cmds) = cmds_list
        for i in range(len(cmds)):
            c = cmds[i]
            if c != None:
                if len(self.commands_per_tick) == i:  # create new cell
                    self.commands_per_tick.append(["HEAD " + ac_id + " " + str(c)])
                else:
                    self.commands_per_tick[i].append("HEAD " + ac_id + " " + str(c))
            else:
                if len(self.commands_per_tick) == i:  # create new cell
                    self.commands_per_tick.append([])
                else:
                    pass

    def _make_optimal_route(self,
                            start_xy: Tuple[float, float],
                            start_dir: int,
                            end_xy: Tuple[float, float],
                            end_dir: int
                            ) -> list[Optional[int]]:
        # make turn(s) at start, make turn(s) at end, connect points
        # place a turning circle on directly left or right side at start & end.
        # Cruise direction and length is the line from/to centers of cruise-starting circles
        # (if cruise starts and ends on "same" side of the circle)

        # turning circle diameter == 28.35640909 or 89.08 circumference (maybe approximates 20*sqrt(2));
        # circumference should be actually 100 as it's 20x5 legs?
        # Probably it is an 18-gon after all, even if the graphics seem to model it as a circle.
        # let's settle for 28.36 diameter, or 14.18 radius, rounding it up more doesn't make it less or more precise or offer any needed tolerance.
        flight_path: list[Optional[int]] = []  # for each leg, either a heading or nothing
        (sx, sy) = start_xy
        (ex, ey) = end_xy

        # this function could be sensically recursified by dicing the path into smaller and smaller chunks
        # however, let's settle for less technical, less person-hours solution

        # calculate start and end turns. To save effort for now, assume only 1 turn is needed at each end
        # we can actually always calculate the circles, even if we won't be doing any turning
        sca_side: int = right_or_left(
            start_xy,
            start_dir,
            end_xy,
            end_dir
        )
        sca: Tuple[float, float] = turn_circle_xy(
            start_xy,
            start_dir,
            end_xy,
            end_dir,
            self.TURN_R
        )
        print("starting circle " + str(sca))

        eca_side_mirrored: int = right_or_left(
            end_xy,
            normalize_heading(end_dir + 180),
            start_xy,
            normalize_heading(start_dir + 180)
        )
        eca: Tuple[float, float] = turn_circle_xy(
            end_xy,
            normalize_heading(end_dir + 180),
            start_xy,
            normalize_heading(start_dir + 180),
            self.TURN_R
        )
        print("ending circle " + str(eca))

        (s_e_a, s_e_xy) = select_ideal_tangent_point(
            start_xy,
            start_dir,
            calculate_direction(start_xy, end_xy),
            find_tangent_points(sca, eca, self.TURN_R)
        )
        print("starting tangent point " + str(s_e_xy))

        (_, e_s_xy) = select_ideal_tangent_point(
            end_xy,
            normalize_heading(end_dir + 180),
            calculate_direction(end_xy, start_xy),
            find_tangent_points(eca, sca, self.TURN_R)
        )
        print("ending tangent point " + str(e_s_xy))

        # Are the tangent points on opposite sides of start/end circles,
        # meaning the optimal route is when tangent line goes in-between the circles.
        # (s_e_a) is the angle of 2 parallel tangents two circles always share
        angle: float = calculate_direction(s_e_xy, e_s_xy)
        if angular_difference(angle, s_e_a) >= 1: # if so
            sca_cmds = self._make_turn(start_dir, round(angle), sca_side)
            eca_cmds = self._make_turn(round(angle), end_dir, 0 - eca_side_mirrored)
        else:
            sca_cmds = self._make_turn(start_dir, round(s_e_a), sca_side)
            eca_cmds = self._make_turn(round(s_e_a), end_dir, 0 - eca_side_mirrored)

        # calculate the cruising part of the route
        leg_sca_eca: float = calculate_length(s_e_xy, e_s_xy)
        print(leg_sca_eca)

        # landing radius is always more than 5, so let's not waste time on optimizing landing regarding 5/tick discrete movements
        cruising_turns: int = floor(leg_sca_eca / 5)
        for c in sca_cmds:
            flight_path.append(c)
        for i in range(cruising_turns):
            flight_path.append(None)
        for c in eca_cmds:
            flight_path.append(c)
        return flight_path

    def _make_turn(self,
                   start_dir: int,
                   end_dir: int,
                   lr: int
                   ) -> list[int]:
        # dice required changes in directory to 20° pieces
        # while taking into account if we're turning left or right
        commands: list[int] = []
        cur_dir: int = start_dir
        turn: float = 0
        print("turning from " + str(start_dir) + " to " + str(end_dir))

        if lr == 1: # left, ccw
            if start_dir < end_dir:
                turn = end_dir - start_dir
            else:
                turn = 360 - (start_dir - end_dir)
        else:  # right, cw
            if start_dir > end_dir:
                turn = start_dir - end_dir
            else:
                turn = 360 - (end_dir - start_dir)

        full_turns: int = floor(turn / 20)
        for t in range(full_turns):
            cur_dir = normalize_heading(cur_dir + 20 * lr)
            commands.append(cur_dir)

        final_turn: int = normalize_heading(cur_dir + (turn % 20) * lr)
        if angular_difference(cur_dir, final_turn) >= 1:
            commands.append(final_turn)

        return commands

if __name__ == "__main__":  # allow piping JSON payload for debugging
    setup: str = input()
    print(NoflightSolver().solve(json.loads(setup)))
