from math import atan, degrees, fabs, pi, radians, sin, cos, hypot
from typing import Tuple

def normalize_heading(heading):
    """Normalize any angle to 0-359"""
    return round(heading + 360) % 360

def angular_difference(a1: float,
                       a2: float
                       ) -> float:
    # credit to https://math.stackexchange.com/q/3497743
    return min(fabs(a1-a2), 360 - fabs(a1-a2))

def calculate_direction(start_xy: Tuple[float, float],
                        end_xy: Tuple[float, float]
                        ) -> float:
    # direction 0 is x+, 90 y+, 180 x-, 270 y-
    # start_xy == end_xy is undefined behaviour
    (sx, sy) = start_xy
    (ex, ey) = end_xy

    x: float = ex - sx
    y: float = ey - sy

    if x == 0:
        if y > 0:
            return 90.0
        else:
            return 270.0
    if y == 0:
        if x > 0:
            return 0.0
        else:
            return 180.0
    else:
        d = degrees(atan(y/x))
        # d is now -90 .. 90 degrees aligning correctly on x+ side, but inversely(?) on x- side.
        if x >= 0 and y >= 0:
            return d
        elif x >= 0 and y < 0:
            return 360 + d
        elif x < 0 and y >= 0:
            return 90 + (90 + d)
        elif x < 0 and y < 0:
            return 180 + d

def calculate_length(start_xy: Tuple[float, float],
                     end_xy: Tuple[float, float]
                     ) -> float:
    (sx, sy) = start_xy
    (ex, ey) = end_xy

    x: float = ex - sx
    y: float = ey - sy

    return hypot(x, y)

def right_or_left(start_xy: Tuple[float, float],
                  start_dir: int,
                  end_xy: Tuple[float, float],
                  end_dir: int
                  ) -> int:
    # return -1 for right, 0 for no turns required, 1 for left
    # < 0.5° means no turns required. We could also calculate minimum degrees for turning using landingRadius
    dir_as_the_bird_flies: int = round(calculate_direction(start_xy, end_xy))

    if start_dir == end_dir and start_dir == round(dir_as_the_bird_flies):
        return 0
    elif dir_as_the_bird_flies > start_dir and dir_as_the_bird_flies < start_dir + 180:
        return 1
    else:
        return -1

def turn_circle_xy(start_xy: Tuple[float, float],
                   start_dir: int,
                   end_xy: Tuple[float, float],
                   end_dir: int,
                   circle_r: float
                   ) -> Tuple[float, float]:
    # calculate circle center coordinates
    lr: int = right_or_left(start_xy, start_dir, end_xy, end_dir)
    if lr == 0:
        # we have to have the circle on either side and not in front, let's default to right.
        lr = 1
    circledir: int = normalize_heading(start_dir + (90 * lr))
    return calculate_leg_end(start_xy, circledir, circle_r)

def calculate_leg_end(start_xy: Tuple[float, float],
                      direction: int,
                      length: float
                      ) -> Tuple[float, float]:
    # calculate where we end up with select direction and length traveled
    (sx, sy) = start_xy
    # we know an angle and hypotenuse of a right triangle, use cos and sin to find out side lengths
    ey: float = sin(radians(direction)) * length
    ex: float = cos(radians(direction)) * length
    return (sx + ex, sy + ey)

def find_tangent_points(start_c_xy: Tuple[float, float],
                        end_c_xy: Tuple[float, float],
                        circle_r: float
                        ) -> Tuple[float, Tuple[Tuple[float, float], Tuple[float, float]]]:
    # there are always 2 parallel tangent lines between 2 circles, let's find where the lines and circles cross
    angle = calculate_direction(start_c_xy, end_c_xy)
    tangent_1 = calculate_leg_end(start_c_xy, normalize_heading(angle + 90), circle_r)
    tangent_2 = calculate_leg_end(start_c_xy, normalize_heading(angle + 270), circle_r)
    return (angle, (tangent_1, tangent_2))

def select_ideal_tangent_point(start_xy: Tuple[float, float],
                               start_dir: float,
                               end_dir: float,
                               tangents: Tuple[float, Tuple[Tuple[float, float], Tuple[float, float]]]
                               ) -> Tuple[float, Tuple[float, float]]:
    # less turning is better, so choose a point with least turning required
    # for simplicity, assume for now, that we won't be criss-crossing between circles

    # for 3rd level criss-crossing was required, so a more complicated heuristic was done
    # with select_farther -mechanism.

    (sx, sy) = start_xy
    (a, ((t1x, t1y), (t2x, t2y))) = tangents


    select_farther: bool = False
    # We have to do an U-loop which should mean the farther tangent is preferable
    if angular_difference(start_dir, end_dir) > 90:
        select_farther = True
        print("U-loop inc")

    t1dir: float = calculate_direction(start_xy, (t1x, t1y))
    t2dir: float = calculate_direction(start_xy, (t2x, t2y))

    if angular_difference(start_dir, t1dir) <= angular_difference(start_dir, t2dir):
        if select_farther:
            return (a, (t2x, t2y))
        else:
            return (a, (t1x, t1y))
    else:
        if select_farther:
            return (a, (t1x, t1y))
        else:
            return (a, (t2x, t2y))
