import pickle as pkl
import pandas as pd


class ProcessGameState:

    Z_MIN = 285 
    Z_MAX = 421

    def __init__(self, game_state_frame_data_path):
        with open(game_state_frame_data_path, 'rb') as file:
            self.game_state_frame_data = pkl.load(file)

    # we define the enter interval as the first 20 seconds of the round (1:40 - 2:00)
    def is_t_side_enter_boundary_common(self, boundary_points):
        total_t_frames = 0
        t_within_boundary_frames = 0
        for i in range(len(self.game_state_frame_data)):
            frame = self.game_state_frame_data.iloc[i]
            minutes, seconds = map(int, frame['clock_time'].split(':'))
            total_seconds = minutes * 60 + seconds
            if frame['side'] == 'T':
                total_t_frames += 1
                if total_seconds >= 100 and ProcessGameState.is_in_bounds((frame['x'], frame['y'], frame['z']), boundary_points):
                    t_within_boundary_frames += 1

        # define 0.5 as the threshold for "common" entrance
        return t_within_boundary_frames / total_t_frames >= 0.5

    def extract_weapon_classes(player_frame_data):
        weapon_class_count = dict()
        for weapon in player_frame_data['inventory']:
            weapon_class_count[weapon['weapon_class']] += 1
        return weapon_class_count

    def is_in_bounds(pt, boundary_points):
        x, y, z = pt[0], pt[1], pt[2] 

        # if boundary points is only one point, just check if point in question is on that boundary point
        if len(boundary_points) == 1:
            return x == boundary_points[0][0] and y == boundary_points[0][1] and z == boundary_points[0][1]

        # if boundary points represent a straight line, check if point in question is on that line
        distinct_x = set()
        distinct_y = set()
        for point in boundary_points:
            distinct_x.add(point[0]) 
            distinct_y.add(point[1]) 
        distinct_points = list(set(boundary_points))
        if len(distinct_x) == 1 or len(distinct_y) == 1:
            point1 = distinct_points[0]
            point2 = distinct_points[1]
            return ProcessGameState.is_point_on_line((x, y), point1, point2)

        polygon = ProcessGameState.get_polygon(distinct_points)
        return ProcessGameState.is_point_in_polygon((x, y), polygon) and z >= ProcessGameState.Z_MIN and z <= ProcessGameState.Z_MAX


    # https://stackoverflow.com/questions/217578/how-can-i-determine-whether-a-2d-point-is-within-a-polygon#:~:text=Compute%20the%20oriented%20sum%20of,less%20dependent%20on%20numerical%20precision.
    def is_point_in_polygon(point, polygon):
        intersections = 0
        x, y = point[0], point[1]

        # new a point outside the boundary to cast a ray from point (min_x, random_y) to (x, y)
        e = 1
        min_x = polygon[0][0] - e
        for pt in polygon:
            min_x = min(min_x, pt[0] - e)
        random_y = y

        for i in range(len(polygon)):
            x1, y1 = polygon[i][0], polygon[i][1]
            x2, y2 = polygon[(i + 1) % len(polygon)][0], polygon[(i + 1) % len(polygon)][1]
            # Check if the ray intersects with the edge
            if ProcessGameState.is_intersecting(((min_x, random_y), (x, y)), ((x1, y1), (x2, y2))):
                intersections += 1

        return intersections % 2 == 1

    # https://stackoverflow.com/questions/14263284/create-non-intersecting-polygon-passing-through-all-given-points/20623817#20623817
    def get_polygon(boundary_points):
        sorted_points = sorted(boundary_points, key=lambda p: p[0])
        left_most_point = sorted_points[0] 
        right_most_point = sorted_points[len(sorted_points)-1] 
        top_points = list()
        bottom_points = list()
        for i in range(1, len(boundary_points)-1):
            if ProcessGameState.point_on_which_side(boundary_points[i], left_most_point, right_most_point) <= 0:
                top_points.append(boundary_points[i])
            else:
                bottom_points.append(boundary_points[i])
        top_points.sort(key=lambda p: p[0])
        bottom_points.sort(key=lambda p: p[0])
        polygon = list()
        polygon.append(left_most_point)
        polygon.extend(top_points)
        polygon.append(right_most_point)
        polygon.extend(bottom_points)
        return polygon
    
    # https://stackoverflow.com/questions/217578/how-can-i-determine-whether-a-2d-point-is-within-a-polygon#:~:text=Compute%20the%20oriented%20sum%20of,less%20dependent%20on%20numerical%20precision.
    def is_intersecting(line1, line2):
        v1x1, v1y1, v1x2, v1y2 = line1[0][0], line1[0][1], line1[1][0], line1[1][1]
        v2x1, v2y1, v2x2, v2y2 = line2[0][0], line2[0][1], line2[1][0], line2[1][1]

        a1 = v1y2 - v1y1
        b1 = v1x1 - v1x2
        c1 = (v1x2 * v1y1) - (v1x1 * v1y2)
        d1 = (a1 * v2x1) + (b1 * v2y1) + c1
        d2 = (a1 * v2x2) + (b1 * v2y2) + c1
        if d1 > 0 and d2 > 0:
            return False
        if d1 < 0 and d2 < 0:
            return False
        a2 = v2y2 - v2y1
        b2 = v2x1 - v2x2
        c2 = (v2x2 * v2y1) - (v2x1 * v2y2)
        d1 = (a2 * v1x1) + (b2 * v1y1) + c2
        d2 = (a2 * v1x2) + (b2 * v1y2) + c2
        if (d1 > 0 and d2 > 0):
            return False
        if (d1 < 0 and d2 < 0):
            return False
        if ((a1 * b2) - (a2 * b1) == 0.0):
            #colinear case
            return False

        return True
    
    def is_point_on_line(query_point, point1, point2):
        x, y = query_point[0], query_point[1]
        x1, y1 = point1[0], point1[1]
        x2, y2 = point2[0], point2[1]
        if x2 - x1 != 0:
            m = (y2 - y1) / (x2 - x1)
        else:
            # verital line case
            return x == x1 and y >= min(y1, y2) and y <= max(y1, y2)
        b = y1 - m * x1
        return y == (m * x + b)

    # https://stackoverflow.com/questions/1560492/how-to-tell-whether-a-point-is-to-the-right-or-left-side-of-a-line
    def point_on_which_side(query_point, point1, point2):
        v0 = (point2[0] - point1[0]) * (query_point[1] - point1[1])
        v1 = (point2[1] - point1[1]) * (query_point[0] - point1[0])
        if v0 - v1 > 0:
            return 1
        elif v0 - v1 < 0:
            return -1
        else:
            return 0

def main():
    pgs = ProcessGameState('./data/game_state_frame_data.pickle')
    boundary_points = [(-1735, 250), (-2024, 398), (-2806, 742), (-2472, 1233), (-1565, 580)]
    print(pgs.is_t_side_enter_boundary_common(boundary_points))

if __name__ == "__main__":
    main()