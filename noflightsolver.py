from math import ceil, floor
from typing import Optional

# debugging
import json

from lib.math import calculateDirection, calculateLength, normalize_heading, rightOrLeft, turnCircleXY, findTangentPoints, select_ideal_tangent_point, angular_difference

class NoflightSolver:

    TURN_R: float = 14.18

    def __init__(self):
        self.commands_list = []
        self.commands = [] # cleaned up commands for consumption
        pass

    def solve(self, game_state):
        if (self.commands_list == []):  # let's assume for starters that the solver will not require compensation for model drift
            print(game_state)
            aircrafts = game_state["aircrafts"]
            airports = game_state["airports"]
            bbox = game_state["bbox"]  # let's use this to check solution sanity
            print(aircrafts)
            print(airports)
            print(bbox)
            for ac in aircrafts:
                for ap in airports:
                    if ac["destination"] == ap["name"]:
                        path = self._makeOptimalRoute((ac["position"]["x"], ac["position"]["y"]),
                                                 ac["direction"],
                                                 (ap["position"]["x"], ap["position"]["y"]),
                                                 ap["direction"])
                        self.commands_list.append((ac["id"], path))  # will need to be zipped with other aircraft paths
#            for (ac_id, ac_cmds) in self.commands_list:
#                print(ac_cmds)
#                for c in ac_cmds:
#                    if c != None: # single aircraft control for now
#                        self.commands.append(["HEAD " + ac_id + " " + str(c)])
#                    else:
#                        self.commands.append([])
            print(self.commands_list)
            for ac in self.commands_list:
                self._map_path_on_cmds(ac)
            print(self.commands)

        return self.commands.pop(0)

    def _map_path_on_cmds(self, cmds_list):
        (ac_id, cmds) = cmds_list
        for i in range(len(cmds)):
            c = cmds[i]
            if c != None:
                if len(self.commands) == i:  # create new cell
                    self.commands.append(["HEAD " + ac_id + " " + str(c)])
                else:
                    self.commands[i].append("HEAD " + ac_id + " " + str(c))
            else:
                if len(self.commands) == i:  # create new cell
                    self.commands.append([])
                else:
                    pass



    def _makeOptimalRoute(self, startxy, startdir, endxy, enddir):
        # make turn(s) at start, make turn(s) at end, connect points
        # how to figure out the cruise direction, it's probably not midway between startdir and enddir, nor straight line from startxy to endxy
        # place a turning circle on left or right side at start & end, cruise direction and length is the line from/to centers of cruise-starting circles
        # what if cruise length doesn't divide neatly into 5-length legs?
        # Apparently distance from airplane to airport can be up to 10 as long as directions are same

        # turning circle diameter == 28.35640909 or 89.08 circumference (maybe approximates 20*sqrt(2)); circumference should be actually 100 as it's 20x5 legs? Probably it is an 18-gon after all, even if the graphics seem to model it as a circle.
        # let's settle for 28.36 diameter, or 14.18 radius, rounding it up more doesn't make it less or more precise or offer any needed tolerance.
        flight_path: list(Optional(int)) = []  # for each leg, either a heading or nothing
        (sx, sy) = startxy
        (ex, ey) = endxy
        print(str(sx) + "," + str(sy) + "," + str(startdir) + ";" + str(ex) + "," + str(ey) + "," + str(enddir))

        # this function could be sensically recursified by dicing the path into smaller and smaller chunks
        # however, let's settle for less technical, less person-hours solution

        # calculate start and end turns. To save effort for now, assume only 1 turn is needed at each end
        sca = None
        eca = None
        # we can actually always calculate the circles, even if we won't be traveling on the circumference
        sca_side = rightOrLeft(startxy, startdir, endxy, enddir)
        sca = turnCircleXY(startxy, startdir, endxy, enddir, self.TURN_R)
        print("starting circle " + str(sca))
        eca_side_mirrored = rightOrLeft(endxy, normalize_heading(enddir + 180), startxy, normalize_heading(startdir + 180))
        eca = turnCircleXY(endxy, normalize_heading(enddir + 180), startxy, normalize_heading(startdir + 180), self.TURN_R)
        print("ending circle " + str(eca))
        (s_e_a, s_e_xy) = select_ideal_tangent_point(startxy, startdir, calculateDirection(startxy, endxy), findTangentPoints(sca, eca, self.TURN_R))
        print(s_e_a)
        print("starting tangent point " + str(s_e_xy))
        # I think the angle is enough here; we'll just turn heading as fast as possible, until desired heading is reached.
        # we need only the start angle:
        (_, e_s_xy) = select_ideal_tangent_point(endxy, normalize_heading(enddir + 180), calculateDirection(endxy, startxy), findTangentPoints(eca, sca, self.TURN_R))
        print("ending tangent point " + str(e_s_xy))

        # Does start-end circles think the optimal route is when tangent line "separates" the circles
        angle = calculateDirection(s_e_xy, e_s_xy)
        print("real angle " + str(angle) + "; " + str(angular_difference(angle, s_e_a)))
        if angular_difference(angle, s_e_a) >= 1:
            sca_cmds = self._makeTurn(startdir, angle, sca_side)
            eca_cmds = self._makeTurn(angle, enddir, 0 - eca_side_mirrored)
        else:
            sca_cmds = self._makeTurn(startdir, s_e_a, sca_side)
            eca_cmds = self._makeTurn(s_e_a, enddir, 0 - eca_side_mirrored)

        leg_sca_eca = calculateLength(s_e_xy, e_s_xy)

        # landing radius is always more than 5, so let's not waste time on optimizing landing regarding 5/tick discrete movements
        cruising_turns = floor(leg_sca_eca / 5)
        print(leg_sca_eca)
#        if (angular_difference(s_e_a, startdir) >= 1):
        for c in sca_cmds:
            flight_path.append(c)
        for i in range(cruising_turns):
            flight_path.append(None)
#        if (angular_difference(s_e_a, enddir) >= 1):
        for c in eca_cmds:
            flight_path.append(c)
        return flight_path

    def _makeTurn(self, start_dir, end_dir, lr):
        commands = []
        cur_dir = start_dir
        print(str(start_dir) + " to " + str(end_dir))
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
        full_turns = floor(turn / 20)
        print(full_turns)
        for t in range(full_turns):
            cur_dir = normalize_heading(cur_dir + 20 * lr)
            commands.append(cur_dir)
        final_turn = normalize_heading(cur_dir + (turn % 20) * lr)
        print(final_turn)
        if angular_difference(cur_dir, final_turn) >= 1:
            commands.append(final_turn)
        print(commands)
        return commands

if __name__ == "__main__":  # allow piping JSON payload for debugging
    setup: str = input()
    print(NoflightSolver().solve(json.loads(setup)))
