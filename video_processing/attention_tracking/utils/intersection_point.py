
# A Python3 program to find if 2 given line segments intersect or not 
import math  
class Point: 
    def __init__(self, x, y): 
        self.x = x 
        self.y = y 
  
# Given three collinear points p, q, r, the function checks if  
# point q lies on line segment 'pr'  
def onSegment(p, q, r): 
    if ( (q.x <= max(p.x, r.x)) and (q.x >= min(p.x, r.x)) and 
           (q.y <= max(p.y, r.y)) and (q.y >= min(p.y, r.y))): 
        return True
    return False
  
def orientation(p, q, r): 
    # to find the orientation of an ordered triplet (p,q,r) 
    # function returns the following values: 
    # 0 : Collinear points 
    # 1 : Clockwise points 
    # 2 : Counterclockwise 
      
    # See https://www.geeksforgeeks.org/orientation-3-ordered-points/amp/  
    # for details of below formula.  
      
    val = (float(q.y - p.y) * (r.x - q.x)) - (float(q.x - p.x) * (r.y - q.y)) 
    if (val > 0): 
          
        # Clockwise orientation 
        return 1
    elif (val < 0): 
          
        # Counterclockwise orientation 
        return 2
    else: 
          
        # Collinear orientation 
        return 0
  
# The main function that returns true if  
# the line segment 'p1q1' and 'p2q2' intersect. 
def doIntersect(p1,q1,p2,q2): 
      
    # Find the 4 orientations required for  
    # the general and special cases 
    o1 = orientation(p1, q1, p2) 
    o2 = orientation(p1, q1, q2) 
    o3 = orientation(p2, q2, p1) 
    o4 = orientation(p2, q2, q1) 
  
    # General case 
    if ((o1 != o2) and (o3 != o4)): 
        return True
  
    # Special Cases 
  
    # p1 , q1 and p2 are collinear and p2 lies on segment p1q1 
    if ((o1 == 0) and onSegment(p1, p2, q1)): 
        return True
  
    # p1 , q1 and q2 are collinear and q2 lies on segment p1q1 
    if ((o2 == 0) and onSegment(p1, q2, q1)): 
        return True
  
    # p2 , q2 and p1 are collinear and p1 lies on segment p2q2 
    if ((o3 == 0) and onSegment(p2, p1, q2)): 
        return True
  
    # p2 , q2 and q1 are collinear and q1 lies on segment p2q2 
    if ((o4 == 0) and onSegment(p2, q1, q2)): 
        return True
  
    # If none of the cases 
    return False

def point_in_box(px, py, x1, y1, x2, y2):
    return x1 <= px <= x2 and y1 <= py <= y2

def get_box_edges(x1, y1, x2, y2):
    top_left = Point(x1, y1)
    top_right = Point(x2, y1)
    bottom_right = Point(x2, y2)
    bottom_left = Point(x1, y2)

    return [
        (top_left, top_right),
        (top_right, bottom_right),
        (bottom_right, bottom_left),
        (bottom_left, top_left)
    ]

#exapnd the gaze radius by 10 pixels to account for noise in gaze estimation and head detection
def get_gaze_edge_point(head_center, gaze_center, radius=10):
    import math

    head_cx, head_cy = head_center
    g_x, g_y = gaze_center

    dx = g_x - head_cx
    dy = g_y - head_cy

    mag = math.sqrt(dx**2 + dy**2)
    if mag == 0:
        return gaze_center  # fallback

    ux = dx / mag
    uy = dy / mag

    # Move from center to edge
    edge_x = g_x + ux * radius
    edge_y = g_y + uy * radius

    return (edge_x, edge_y)

def expand_box(x1, y1, x2, y2, margin=10):
    return (x1 - margin, y1 - margin, x2 + margin, y2 + margin)

def gaze_hits_object(head_box, gaze_point, object_box, expand_margin=None):
    head_x1, head_y1, head_x2, head_y2 = head_box
    g_x, g_y = gaze_point
    obj_x1, obj_y1, obj_x2, obj_y2 = object_box

    if expand_margin is not None:
        # Expand the object box by the margin
        obj_x1, obj_y1, obj_x2, obj_y2 = expand_box(obj_x1, obj_y1, obj_x2, obj_y2, expand_margin)

    head_cx = (head_x1 + head_x2) / 2.0
    head_cy = (head_y1 + head_y2) / 2.0

    gaze_start = Point(head_cx, head_cy)
    gaze_end = Point(g_x, g_y)

    if point_in_box(g_x, g_y, obj_x1, obj_y1, obj_x2, obj_y2):
        return True

    for edge_start, edge_end in get_box_edges(obj_x1, obj_y1, obj_x2, obj_y2):
        if doIntersect(gaze_start, gaze_end, edge_start, edge_end):
            return True

    return False


def box_center(box):
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def euclidean_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def angular_error(head_center, gaze_point, object_center):
    import math

    # Vector A: head → gaze
    Ax = gaze_point[0] - head_center[0]
    Ay = gaze_point[1] - head_center[1]

    # Vector B: head → object
    Bx = object_center[0] - head_center[0]
    By = object_center[1] - head_center[1]

    # Dot product
    dot = Ax * Bx + Ay * By

    # Magnitudes
    magA = math.sqrt(Ax**2 + Ay**2)
    magB = math.sqrt(Bx**2 + By**2)

    if magA == 0 or magB == 0:
        return float('inf')  # avoid division error

    cos_theta = dot / (magA * magB)

    # Numerical safety
    cos_theta = max(-1, min(1, cos_theta))

    theta = math.acos(cos_theta)  # in radians

    return theta

def normalized_score(head_center, gaze_point, object_center,
                     max_dist, w1=0.7, w2=0.3):

    dist = euclidean_distance(gaze_point[0],gaze_point[1], object_center[0], object_center[1]) / max_dist
    angle = angular_error(head_center, gaze_point, object_center) / math.pi

    return (w1 * dist) + (w2 * angle)

def find_best_gaze_target_V1(head_box, gaze_point, objects, frame_width, frame_height, expand_margin=None):
    
    head_center = box_center([head_box[0],head_box[1], head_box[2], head_box[3]])

    gaze_point = get_gaze_edge_point(head_center, gaze_point, radius=20)

    max_dist = math.sqrt(frame_width**2 + frame_height**2)

    best_obj = None
    best_score = float('inf')

    for index,obj in enumerate(objects):
        _,_,object_id,obj_bbox, _ = obj
        x1, y1, x2, y2 = obj_bbox
        if gaze_hits_object(head_box, gaze_point, (x1, y1, x2, y2),expand_margin):
            if expand_margin is not None:
                x1, y1, x2, y2 = expand_box(x1, y1, x2, y2, expand_margin)

            obj_center = box_center((x1,y1,x2,y2))

            score = normalized_score(
                head_center,
                gaze_point,
                obj_center,
                max_dist,
                w1=0.7,
                w2=0.3
            )

            if score < best_score:
                best_score = score
                best_obj = index

    return best_obj

def find_best_gaze_target_V2(head_box, gaze_point, objects,expand_margin=None):
    g_x, g_y = gaze_point
    min_dist = float('inf')
    candidate = None

    for index,obj in enumerate(objects):
        _,_,object_id,obj_bbox, _ = obj
        x1, y1, x2, y2 = obj_bbox
        if gaze_hits_object(head_box, gaze_point, (x1, y1, x2, y2),expand_margin):
            cx, cy = box_center((x1, y1, x2, y2))
            dist = euclidean_distance(g_x, g_y, cx, cy)
            if dist < min_dist:
                min_dist = dist 
                candidate = index

    
    return candidate


    
#     return is_intersect_with_segment_one or is_intersect_with_segment_two or is_intersect_with_segment_three or is_intersect_with_segment_four
# Driver program to test above functions: 
# p1 = Point(1, 1) 
# q1 = Point(10, 1) 
# p2 = Point(1, 2) 
# q2 = Point(10, 2) 
  
# if doIntersect(p1, q1, p2, q2): 
#     print("Yes") 
# else: 
#     print("No") 
  
# p1 = Point(10, 0) 
# q1 = Point(0, 10) 
# p2 = Point(0, 0) 
# q2 = Point(10,10) 
  
# if doIntersect(p1, q1, p2, q2): 
#     print("Yes") 
# else: 
#     print("No") 
  
# p1 = Point(-5,-5) 
# q1 = Point(0, 0) 
# p2 = Point(1, 1) 
# q2 = Point(10, 10) 
  
# if doIntersect(p1, q1, p2, q2): 
#     print("Yes") 
# else: 
#     print("No") 
      
# This code is contributed by Ansh Riyal 
