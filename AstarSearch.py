from builtins import range
import json
import MalmoPython
import os
import sys
import time
import math
import numpy as np

DEBUG = True

class Vertex:
    def __init__(self,x,y,z,row,col,parent,g,h,direction):
        self.x = x
        self.y = y
        self.z = z
        self.row = row # row, position in the graph
        self.col = col # col, position in the graph
        self.parent = parent
        self.g = g
        self.h = h
        self.f = g+h
        self.direction = direction
    def __eq__(self,other):
        return self.__dict__ == other.__dict__


def create_Graph(agent_host):
    # create graph from min (x,y,z) to max (x,y,z), following row major order
    #
    # Ex: start: min(-1,5,1), end: max(1,5,1). Before reshape observation is a 1d array [0,1,2,3,4,5,6,7,8] 
    # After reshape to 3X3:
    #                      North
    #         (-1,5,-1)   (0,5,-1)           (1,5,-1)
    # West    (-1,5,0)    (0,5,0)(Agent)     (1,5,0)      East
    #         (-1,5,1)    (0,5,1)            (1,5,1)
    #                      South
    #
    world_state = agent_host.getWorldState()
    while world_state.number_of_observations_since_last_state == 0:
        time.sleep(0.1)
        world_state = agent_host.getWorldState()
        if world_state.is_mission_running == False:
            return None
    msg = world_state.observations[-1].text
    observations = json.loads(msg)
    graph = observations["grid_observation"] # 1d array
    graph = np.reshape(graph,(199,199)) #center (99,99)  
    center_x = 99 
    center_y = 99 
    return graph,center_x,center_y

def heuristic(x,y,z,target_x,target_y,target_z):
    # Manhattan Distance
    return abs(x-target_x) +abs(y-target_y) + abs(z-target_z)

def find_minf_vertex_and_remove(open_List):
    # find vertex that has the minimum f(f=g+h)
    # may have errors here due to unfamiliar with python
    minf = sys.maxsize
    minf_Vertex = None
    index = -1
    # find the min f vertex
    for i in range(0,len(open_List)):
        if(open_List[i].f <= minf):
            minf = open_List[i].f
            minf_Vertex = open_List[i]
            index = i
    open_List.pop(index)
    if(DEBUG):
        print("successfully poped")
    return minf_Vertex

def isInBoudary(row,col):
    if(row<0 or row >198):
        return False
    if(col<0 or col >198):
        return False
    return True

def isInOpenList(v,open_List):
    # if there already exist a node with the same(x,y,z) as the successor in open_List,
    # and has a lower f (f=g+h) than successor, return true (we skip this successor)
    # else return false (we need to furthur check the condition)

    # may have errors here due to unfamiliar with python
    # print("==============")
    # print("v.x is ",v.x)
    # print("v.y is ",v.y)
    # print("v.z is ",v.z)
    # print("v.f is ",v.f)
    # print("open list is:",open_List)
    # print("=============")
    # time.sleep(0.5)
    for node in open_List:
        if(node.x == v.x and node.y ==v.y and node.z == v.z ):
            if(node.f <=v.f):
                if(DEBUG):
                    print("isInOpenList: True")
                return True
            else:
                if(DEBUG):
                    print("isInOpenList: False")
                return False
    return False

def isVisited(v,visited):
    # if there already exist a node with the same(x,y,z) as the successor in visited,
    # and has a lower f (f=g+h) in visited, return true (we skip this successor)
    # else return false (we need to add the successor to open_List)

    # may have errors here due to unfamiliar with python
    for node in visited:
        if(node.x == v.x and node.y ==v.y and node.z == v.z ):
            if(node.f <=v.f):
                return True
            else:
                return False
    return False

def isDestination(v_x,v_y,v_z,dest_x,dest_y,dest_z):
    dx = v_x - dest_x
    dy = v_y - dest_y
    dz = v_z - dest_z
    distance = math.sqrt(dx * dx + dy * dy + dz * dz)
    if(distance<1):
        return True
    else:
        return False
    
def isOnGraph(x,y,z,dest_x,dest_y,dest_z):
    if(abs(x-dest_x)>99 or abs(y-dest_y)>0 or abs(z-dest_z)>99):
        print("The destination is not on the graph")
        return False
    else:
        return True

def Astar_search(agent_host,agent_location, target_location):
    graph,center_x,center_y = create_Graph(agent_host)
    open_List = []
    visited =[]
    # start and destination coordinates 
    s_x,s_y,s_z = agent_location[0],agent_location[1],agent_location[2]
    d_x,d_y,d_z = target_location[0],target_location[1],target_location[2]
    print(s_x,s_y,s_z)
    # check if the destination is on the graph
    if(isOnGraph(s_x,s_y,s_z,d_x,d_y,d_z) == False):
        return visited

    h = heuristic(s_x,s_y,s_z,d_x,d_y,d_z)
    start_vertex = Vertex(s_x,s_y,s_z,center_x,center_y,None,0,h,"None")
    
    open_List.append(start_vertex)
    count = 0
    while(len(open_List)>0):
        
        q = find_minf_vertex_and_remove(open_List)
        if(DEBUG):
            print("=====================================================")
            print("loop count is: ",count)
            print("Size of open List is:",len(open_List))
            print("q.x = ",q.x,"; q.y = ",q.y,"; q.z = ",q.z,"; q.g = ",q.g,"; q.h = ",q.h,"; q.f = ",q.f,"; q.parent =",q.parent,"; direction is ",q.direction)
            print("q.row = ",q.row,"; q.col = ",q.col)
        # create 4 successors
        # north succssor
        north_succssor_row = q.row - 1
        north_succssor_col = q.col

        # check if in boundary(graph) and its not an obstacle
        if(isInBoudary(north_succssor_row,north_succssor_col)):
            if(graph[north_succssor_row][north_succssor_col] == 'air'):
                h = heuristic(q.x,q.y,(q.z-1),d_x,d_y,d_z)
                north_succssor_vertex = Vertex(q.x,q.y,(q.z-1),north_succssor_row,north_succssor_col,q,(q.g+1),h,"North")
                if(isDestination(north_succssor_vertex.x,north_succssor_vertex.y,north_succssor_vertex.z,d_x,d_y,d_z) == True):
                    # We find the destinaton, append q and this vertex to visited list and return
                    visited.append(q)
                    visited.append(north_succssor_vertex)
                    return visited
                else:
                    if(isInOpenList(north_succssor_vertex,open_List) == False):
                        if(isVisited(north_succssor_vertex,visited) == False):
                            open_List.append(north_succssor_vertex)
        # south successor
        south_succssor_row = q.row + 1
        south_succssor_col = q.col
        
        # check if in boundary(graph) and its not an obstacle
        if(isInBoudary(south_succssor_row,south_succssor_col)):
            if(graph[south_succssor_row][south_succssor_col] == 'air'):
                h = heuristic(q.x,q.y,(q.z+1),d_x,d_y,d_z)
                south_succssor_vertex = Vertex(q.x,q.y,(q.z+1),south_succssor_row,south_succssor_col,q,(q.g+1),h,"South")
                if(isDestination(south_succssor_vertex.x,south_succssor_vertex.y,south_succssor_vertex.z,d_x,d_y,d_z) == True):
                    # We find the destinaton, append q and this vertex to visited list and return
                    visited.append(q)
                    visited.append(south_succssor_vertex)
                    return visited
                else:
                    if(isInOpenList(south_succssor_vertex,open_List) == False):
                        if(isVisited(south_succssor_vertex,visited) == False):
                            open_List.append(south_succssor_vertex)

        # east successor
        east_succssor_row = q.row 
        east_succssor_col = q.col + 1
        
        # check if in boundary(graph) and its not an obstacle
        if(isInBoudary(east_succssor_row,east_succssor_col)):
            if(graph[east_succssor_row][east_succssor_col] == 'air'):
                h = heuristic((q.x+1),q.y,q.z,d_x,d_y,d_z)
                east_succssor_vertex = Vertex((q.x+1),q.y,q.z,east_succssor_row,east_succssor_col,q,(q.g+1),h,"East")
                if(isDestination(east_succssor_vertex.x,east_succssor_vertex.y,east_succssor_vertex.z,d_x,d_y,d_z) == True):
                    # We find the destinaton, append q and this vertex to visited list and return
                    visited.append(q)
                    visited.append(east_succssor_vertex)
                    return visited
                else:
                    if(isInOpenList(east_succssor_vertex,open_List) == False):
                        if(isVisited(east_succssor_vertex,visited) == False):
                            open_List.append(east_succssor_vertex)
        # west successor
        west_succssor_row = q.row 
        west_succssor_col = q.col - 1
        
        # check if in boundary(graph) and its not an obstacle
        if(isInBoudary(west_succssor_row,west_succssor_col)):
            if(graph[west_succssor_row][west_succssor_col] == 'air'):
                h = heuristic((q.x-1),q.y,q.z,d_x,d_y,d_z)
                west_succssor_vertex = Vertex((q.x-1),q.y,q.z,west_succssor_row,west_succssor_col,q,(q.g+1),h,"West")
                if(isDestination(west_succssor_vertex.x,west_succssor_vertex.y,west_succssor_vertex.z,d_x,d_y,d_z) == True):
                    # We find the destinaton, append q and this vertex to visited list and return
                    visited.append(q)
                    visited.append(west_succssor_vertex)
                    return visited
                else:
                    if(isInOpenList(west_succssor_vertex,open_List) == False):
                        if(isVisited(west_succssor_vertex,visited) == False):
                            open_List.append(west_succssor_vertex)
        # push q to the visited list                
        visited.append(q)
        # print("Visited is: ",visited)
        # print("=====================================================================")
        count+=1
    #end of while
    return visited

def traceThePath(visited,dest_x,dest_y,dest_z):
    path = []
    if(len(visited) == 0):
        print("There is no path on the graph towards destination")
        return path
    last_vertex = visited[len(visited)-1]
    if(isDestination(last_vertex.x,last_vertex.y,last_vertex.z,dest_x,dest_y,dest_z) == False):
        print("The destination is on the graph, but there is no path towards the destination")
        return path
    else:
        while(last_vertex is not None):
            path.append(last_vertex)
            last_vertex = last_vertex.parent
    path.reverse()
    
    return path
    
def movement(agent_host,v):
    agent_location = find_agent_location(agent_host)
    # dx = v.x - agent_location[0]
    # dy = v.y - agent_location[1]
    # dz = v.z - agent_location[2]
    # distance = math.sqrt(dx * dx + dy * dy + dz * dz)
    # yaw = -math.atan2(dx, dz) * 180 / math.pi
    # pitch = math.atan2(dy, distance)
    # pitch_degrees = math.degrees(pitch)

            # check to keep agent positioned correctly before a discrete move command
    # time.sleep(0.1)
    # if agent_location[0] % 1 != 0.5:
    #     agent_host.sendCommand(f"tpx {math.floor (agent_location[0]) + 0.5}")
    # if agent_location[2] % 1 != 0.5:
    #     agent_host.sendCommand(f"tpz {math.floor (agent_location[2]) + 0.5}")

    if(v.direction == "None"):
        pass
    elif(v.direction == "North"):
        agent_host.sendCommand("movenorth 1")
        agent_host.sendCommand("setYaw -180")
    elif(v.direction == "South"):
        agent_host.sendCommand("movesouth 1")
        agent_host.sendCommand("setYaw 0")
    elif(v.direction == "East"):
        agent_host.sendCommand("moveeast 1")
        agent_host.sendCommand("setYaw -90")
    elif(v.direction == "West"):
        agent_host.sendCommand("movewest 1")
        agent_host.sendCommand("setYaw 90")

    #agent_host.sendCommand(f"setPitch {pitch_degrees}")

    return 
    

##########################################################
def find_entity_location(agent_host,entityName):
    world_state = agent_host.getWorldState()
    while world_state.number_of_observations_since_last_state == 0:
        time.sleep(0.1)
        world_state = agent_host.getWorldState()
        if world_state.is_mission_running == False:
            return None
    msg = world_state.observations[-1].text
    observations = json.loads(msg)
    #print(observations)
    if 'entities' in observations:
        for entity in observations['entities']:
            if entity['name'] == entityName:
                return (entity['x'], entity['y'], entity['z'])
    return None
def find_agent_location(agent_host):
    world_state = agent_host.getWorldState()
    while world_state.number_of_observations_since_last_state == 0:
        time.sleep(0.1)
        world_state = agent_host.getWorldState()
        if world_state.is_mission_running == False:
            return None
    msg = world_state.observations[-1].text
    observations = json.loads(msg)
    if 'entities' in observations:
        for entity in observations['entities']:
            if entity['name'] == 'Agent':
                return (entity['x'], entity['y'], entity['z'])
    return None

def move_to(agent_host,entityName):
    entity_location = find_entity_location(agent_host,entityName)
    agent_location = find_agent_location(agent_host)
    if entity_location is None:
        print("There is no " +entityName+ " nearby the agent")
        return
    if agent_location is None:
        return
    
    visited_nodes = Astar_search(agent_host,agent_location,entity_location)
    path = traceThePath(visited_nodes,entity_location[0],entity_location[1],entity_location[2])
    if(len(path) == 0):
        print("No path Found")
        return
    
    for v in path:
        print(v.x,v.y,v.z,v.direction)
        movement(agent_host,v)

    return 

# Brute force
# def move_to(agent_host,entityName):       
#     loopCount = 0
#     while(1):
#         # time.sleep(2)
#         # msg = world_state.observations[-1].text
#         # observations = json.loads(msg)
#         # print(observations)
#         entity_location = find_entity_location(agent_host,entityName)
#         agent_location = find_agent_location(agent_host)
#         if entity_location is None:
#             print("There is no " +entityName+ " nearby the agent")
#             return
#         if agent_location is None:
#             return

#         target_x,target_y,target_z = entity_location[0],entity_location[1],entity_location[2]
#         current_x, current_y, current_z = agent_location[0],agent_location[1],agent_location[2]

#         # check to keep agent positioned correctly before a discrete move command
#         if current_x % 1 != 0.5:
#             agent_host.sendCommand(f"tpx {math.floor (current_x) + 0.5}")
#         if current_z % 1 != 0.5:
#             agent_host.sendCommand(f"tpz {math.floor (current_z) + 0.5}")

#         dx = target_x - current_x
#         dy = target_y - current_y
#         dz = target_z - current_z
#         distance = math.sqrt(dx * dx + dy * dy + dz * dz)
#         yaw = -math.atan2(dx, dz) * 180 / math.pi
#         pitch = math.atan2(dy, distance)
#         pitch_degrees = math.degrees(pitch)
#         # print(pitch)
#         # print("agent location: (",current_x,current_y,current_z,")\n")
#         # print("pigs location: (",target_x,target_y,target_z,")\n")
#         # print("dx,dy,dz,distance are: (",dx,dy,dz,distance,")\n")

#         if distance <= 1:
#             agent_host.sendCommand("strafe 0")
#             agent_host.sendCommand(f"setYaw {yaw}")
#             agent_host.sendCommand(f"setPitch {pitch_degrees}")
#             print("\nAlready at "+ entityName+"'s location.")
#             return 

#         else:
#             if(loopCount == 0):
#                 print("\nMoving towards "+ entityName+"'s location...",end="")
#             else:
#                 print(".",end="")
            
#             if(dx>0):
#                 agent_host.sendCommand(f"setYaw {yaw}")
#                 agent_host.sendCommand(f"setPitch {pitch_degrees}")
#                 agent_host.sendCommand("moveeast 1")
#             elif(dx<0):
#                 agent_host.sendCommand(f"setYaw {yaw}")
#                 agent_host.sendCommand(f"setPitch {pitch_degrees}")
#                 agent_host.sendCommand("movewest 1")
#             elif(dx == 0):
#                 agent_host.sendCommand("strafe 0")

#             if(dz>0):
#                 agent_host.sendCommand(f"setYaw {yaw}")
#                 agent_host.sendCommand(f"setPitch {pitch_degrees}")
#                 agent_host.sendCommand("movesouth 1")
#             elif(dz<0):
#                 agent_host.sendCommand(f"setYaw {yaw}")
#                 agent_host.sendCommand(f"setPitch {pitch_degrees}")
#                 agent_host.sendCommand("movenorth 1")
#             elif(dz==0):
#                 agent_host.sendCommand("strafe 0")
#         loopCount+=1