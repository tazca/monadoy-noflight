from math import atan, degrees, fabs, pi, radians, sin, cos, hypot

def normalize_heading(heading):
    """Normalize any angle to 0-359"""
    return round(heading + 360) % 360

def calculateDirection(startxy, endxy):
    # direction 0 is x+, 90 y+, 180 x-, 270 y-
    # startxy == endxy is undefined behaviour
    (sx, sy) = startxy
    (ex, ey) = endxy

    x = ex - sx
    y = ey - sy

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

def calculateLength(startxy, endxy):
    (sx, sy) = startxy
    (ex, ey) = endxy

    x = ex - sx
    y = ey - sy

    return hypot(x, y)

def rightOrLeft(startxy, startdir, endxy, enddir):
    # return -1 for right, 0 for no turns required, 1 for left
    # < 0.5° means no turns required. We could also calculate minimum degrees for turning using landingRadius
    dir_as_the_bird_flies = round(calculateDirection(startxy, endxy))

    if startdir == enddir and startdir == round(dir_as_the_bird_flies):
        return 0
    elif dir_as_the_bird_flies > startdir and dir_as_the_bird_flies < startdir + 180:
        return 1
    else:
        return -1

def turnCircleXY(startxy, startdir, endxy, enddir, circle_r):
    lr = rightOrLeft(startxy, startdir, endxy, enddir)
    if lr == 0:
        # we have to have the circle on either side and not in front, let's default to right.
        lr = 1
    circledir = normalize_heading(startdir + (90 * lr))
    return calculatePathEnd(startxy, circledir, circle_r)

def calculatePathEnd(startxy, direction, length):
    (sx, sy) = startxy
    # we know an angle and hypotenuse of a right triangle, use cos and sin to find out side lengths
    ey = sin(radians(direction)) * length
    ex = cos(radians(direction)) * length
    return (sx + ex, sy + ey)

def findTangentPoints(start_c_xy, end_c_xy, circle_r):
    angle = calculateDirection(start_c_xy, end_c_xy)
    tangent_1 = calculatePathEnd(start_c_xy, normalize_heading(angle + 90), circle_r)
    tangent_2 = calculatePathEnd(start_c_xy, normalize_heading(angle + 270), circle_r)
    print(tangent_1)
    print(tangent_2)
    return (angle, (tangent_1, tangent_2))

def select_closest_tangent_point(startxy, startdir, tangents):
    # less turning is better, so choose a point with least turning required
    # for simplicity, assume for now, that we won't be criss-crossing between circles
    (sx, sy) = startxy
    (a, ((t1x, t1y), (t2x, t2y))) = tangents
    t1dir = calculateDirection(startxy, (t1x, t1y))
    t2dir = calculateDirection(startxy, (t2x, t2y))

    # BUG: there is a rather large offset with circleXY calculation, requiring 3-point margins here.
    # When turning is not necessary, tangent point will be on top of aircraft and it may mess up
    # the angular heuristic. Let's check that here:
    if fabs(sx - t1x) < 3 and fabs(sy - t1y) < 3:
        return (a, (t1x, t1y))
    elif fabs(sx - t2x) < 3 and fabs(sy - t2y) < 3:
        return (a, (t2x, t2y))

    if angular_difference(startdir, t1dir) <= angular_difference(startdir, t2dir):
        return (a, (t1x, t1y))
    else:
        return (a, (t2x, t2y))

def angular_difference(a1, a2):
    # credit to https://math.stackexchange.com/q/3497743
    return min(fabs(a1-a2), 360 - fabs(a1-a2))
