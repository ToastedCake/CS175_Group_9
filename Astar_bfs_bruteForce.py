from builtins import range
import json
import MalmoPython
import os
import sys
import time
import math
import numpy as np

DEBUG = True

obs_x_range = 119 # must be odd and match the range of observationFromGrid
obs_y_range = 6   # must match the range of observationFromGrid
obs_z_range = 119 # must be odd and match the range of observationFromGrid

non_block_list = {'air','tallgrass'}

class Vertex:
    def __init__(self,x,y,z,layer,row,col,parent,g,h,direction):
        self.x = x
        self.y = y
        self.z = z
        self.layer = layer # layer
        self.row = row # row
        self.col = col # col
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
    # layer 0 [0][row][col] are all non-air blocks. Since it's a flat world
    # layer 1 [1][row][col] are all non-air blocks. Since it's a flat world
    # layer 2 [1][row][col] 1 blocks above the ground <- layer where the agent is initially.
    # layer 3 [1][row][col] 2 blocks above the ground
    # layer 4 [4][row][col] 3 blocks above the ground
    world_state = agent_host.getWorldState()
    while world_state.number_of_observations_since_last_state == 0:
        time.sleep(0.1)
        world_state = agent_host.getWorldState()
        if world_state.is_mission_running == False:
            return None
    msg = world_state.observations[-1].text
    observations = json.loads(msg)
    graph = observations["grid_observation"] # 1d array
    graph = np.reshape(graph,(obs_y_range,obs_x_range,obs_z_range)) #center (2,59,59)  
    center_layer = int((obs_y_range-1)/2)
    center_row = int((obs_x_range-1)/2)
    center_col = int((obs_z_range-1)/2)
    return graph,center_layer,center_row,center_col

def heuristic(x,y,z,target_x,target_y,target_z):
    # Manhattan Distance
    return abs(x-target_x) +abs(y-target_y) + abs(z-target_z)

def find_minf_vertex_and_remove(open_List):
    # find vertex that has the minimum f(f=g+h)
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

def isInBoudary(layer,row,col):
    if(layer<0 or layer>(obs_y_range-1)):
        return False
    if(row<0 or row >(obs_x_range-1)):
        return False
    if(col<0 or col >(obs_z_range-1)):
        return False
    return True

def isInOpenList(v,open_List):
    # if there already exist a node with the same(x,y,z) as the successor in open_List,
    # and has a lower f (f=g+h) than successor, return true (we skip this successor)
    # else return false (we need to furthur check the condition)
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
    # the agent will always start in the second layer(layer 1)
    if(abs(x-dest_x)>99 or abs(y-dest_y)>2 or abs(z-dest_z)>99):
        print("The destination is not presented on the graph")
        return False
    else:
        return True

def isNonBlock(block):
    for i in non_block_list:
        if block == i:
            return True
    return False

def isValid(layer,row,col,graph):
    if(isInBoudary(layer,row,col) == False):
        return False
    if(isNonBlock(graph[layer][row][col])):
        if(not isNonBlock(graph[layer-1][row][col])):
            if(isNonBlock(graph[layer+1][row][col])):
                return True
    
    return False




def Astar_search(agent_host,agent_location, target_location):
    graph,center_layer,center_x,center_y = create_Graph(agent_host)
    open_List = []
    visited =[]
    # start and destination coordinates 
    s_x,s_y,s_z = agent_location[0],agent_location[1],agent_location[2]
    d_x,d_y,d_z = target_location[0],target_location[1],target_location[2]
    if(DEBUG):
        print(s_x,s_y,s_z)
    # check if the destination is on the graph
    if(isOnGraph(s_x,s_y,s_z,d_x,d_y,d_z) == False):
        return visited

    h = heuristic(s_x,s_y,s_z,d_x,d_y,d_z)
    start_vertex = Vertex(s_x,s_y,s_z,center_layer,center_x,center_y,None,0,h,"None")
    
    open_List.append(start_vertex)
    count = 0
    while(len(open_List)>0):
        
        q = find_minf_vertex_and_remove(open_List)
        if(DEBUG):
            print("=====================================================")
            print("loop count is: ",count)
            print("Size of open List is:",len(open_List))
            print("q.x = ",q.x,"; q.y = ",q.y,"; q.z = ",q.z,"; q.g = ",q.g,"; q.h = ",q.h,"; q.f = ",q.f,"; q.parent =",q.parent,"; direction is ",q.direction)
            print("q.layer = ",q.layer,"q.row = ",q.row,"; q.col = ",q.col)
        # create 4 basic successors
        # north succssor
        north_succssor_row = q.row - 1
        north_succssor_col = q.col
        north_succssor_layer = q.layer
        # check if the succssor is valid
        if(isValid(north_succssor_layer,north_succssor_row,north_succssor_col,graph)):
            h = heuristic(q.x,q.y,(q.z-1),d_x,d_y,d_z)
            north_succssor_vertex = Vertex(q.x,q.y,(q.z-1),north_succssor_layer,north_succssor_row,north_succssor_col,q,(q.g+1),h,"North")
            if(isDestination(north_succssor_vertex.x,north_succssor_vertex.y,north_succssor_vertex.z,d_x,d_y,d_z) == True):
                # We find the destinaton, append q and this vertex to visited list and return
                visited.append(q)
                visited.append(north_succssor_vertex)
                return visited
            else:
                if(isInOpenList(north_succssor_vertex,open_List) == False):
                    if(isVisited(north_succssor_vertex,visited) == False):
                        open_List.append(north_succssor_vertex)
        # if the succssor is not valid, it's either (a non-air block) or (the block underneath it is an air block)  
        else:
            # up
            north_up_succssor_row = north_succssor_row
            north_up_succssor_col = north_succssor_col
            north_up_succssor_layer = north_succssor_layer + 1
            if(isValid(north_up_succssor_layer,north_up_succssor_row,north_up_succssor_col,graph)):
                h = heuristic(q.x,(q.y+1),(q.z-1),d_x,d_y,d_z)
                north_up_succssor_vertex = Vertex(q.x,(q.y+1),(q.z-1),north_up_succssor_layer,north_up_succssor_row,north_up_succssor_col,q,(q.g+2),h,"North_Up")
                if(isDestination(north_up_succssor_vertex.x,north_up_succssor_vertex.y,north_up_succssor_vertex.z,d_x,d_y,d_z) == True):
                    # We find the destinaton, append q and this vertex to visited list and return
                    visited.append(q)
                    visited.append(north_up_succssor_vertex)
                    return visited
                else:
                    if(isInOpenList(north_up_succssor_vertex,open_List) == False):
                        if(isVisited(north_up_succssor_vertex,visited) == False):
                            open_List.append(north_up_succssor_vertex)
            #down
            north_down_succssor_row = north_succssor_row
            north_down_succssor_col = north_succssor_col
            north_down_succssor_layer = north_succssor_layer - 1
            if(isValid(north_down_succssor_layer,north_down_succssor_row,north_down_succssor_col,graph)):
                h = heuristic(q.x,(q.y-1),(q.z-1),d_x,d_y,d_z)
                north_down_succssor_vertex = Vertex(q.x,(q.y-1),(q.z-1),north_down_succssor_layer,north_down_succssor_row,north_down_succssor_col,q,(q.g+2),h,"North_Down")
                if(isDestination(north_down_succssor_vertex.x,north_down_succssor_vertex.y,north_down_succssor_vertex.z,d_x,d_y,d_z) == True):
                    # We find the destinaton, append q and this vertex to visited list and return
                    visited.append(q)
                    visited.append(north_down_succssor_vertex)
                    return visited
                else:
                    if(isInOpenList(north_down_succssor_vertex,open_List) == False):
                        if(isVisited(north_down_succssor_vertex,visited) == False):
                            open_List.append(north_down_succssor_vertex)

        # south successor
        south_succssor_row = q.row + 1
        south_succssor_col = q.col
        south_succssor_layer = q.layer
        # check if the succssor is valid
        if(isValid(south_succssor_layer,south_succssor_row,south_succssor_col,graph)):
            h = heuristic(q.x,q.y,(q.z+1),d_x,d_y,d_z)
            south_succssor_vertex = Vertex(q.x,q.y,(q.z+1),south_succssor_layer,south_succssor_row,south_succssor_col,q,(q.g+1),h,"South")
            if(isDestination(south_succssor_vertex.x,south_succssor_vertex.y,south_succssor_vertex.z,d_x,d_y,d_z) == True):
                # We find the destinaton, append q and this vertex to visited list and return
                visited.append(q)
                visited.append(south_succssor_vertex)
                return visited
            else:
                if(isInOpenList(south_succssor_vertex,open_List) == False):
                    if(isVisited(south_succssor_vertex,visited) == False):
                        open_List.append(south_succssor_vertex)
        # if the succssor is not valid, it's either (a non-air block) or (the block underneath it is an air block)  
        else:
            # up
            south_up_succssor_row = south_succssor_row
            south_up_succssor_col = south_succssor_col
            south_up_succssor_layer = south_succssor_layer + 1
            if(isValid(south_up_succssor_layer,south_up_succssor_row,south_up_succssor_col,graph)):
                h = heuristic(q.x,(q.y+1),(q.z+1),d_x,d_y,d_z)
                south_up_succssor_vertex = Vertex(q.x,(q.y+1),(q.z+1),south_up_succssor_layer,south_up_succssor_row,south_up_succssor_col,q,(q.g+2),h,"South_Up")
                if(isDestination(south_up_succssor_vertex.x,south_up_succssor_vertex.y,south_up_succssor_vertex.z,d_x,d_y,d_z) == True):
                    # We find the destinaton, append q and this vertex to visited list and return
                    visited.append(q)
                    visited.append(south_up_succssor_vertex)
                    return visited
                else:
                    if(isInOpenList(south_up_succssor_vertex,open_List) == False):
                        if(isVisited(south_up_succssor_vertex,visited) == False):
                            open_List.append(south_up_succssor_vertex)
            #down
            south_down_succssor_row = south_succssor_row
            south_down_succssor_col = south_succssor_col
            south_down_succssor_layer = south_succssor_layer - 1
            if(isValid(south_down_succssor_layer,south_down_succssor_row,south_down_succssor_col,graph)):
                h = heuristic(q.x,(q.y-1),(q.z+1),d_x,d_y,d_z)
                south_down_succssor_vertex = Vertex(q.x,(q.y-1),(q.z+1),south_down_succssor_layer,south_down_succssor_row,south_down_succssor_col,q,(q.g+2),h,"South_Down")
                if(isDestination(south_down_succssor_vertex.x,south_down_succssor_vertex.y,south_down_succssor_vertex.z,d_x,d_y,d_z) == True):
                    # We find the destinaton, append q and this vertex to visited list and return
                    visited.append(q)
                    visited.append(south_down_succssor_vertex)
                    return visited
                else:
                    if(isInOpenList(south_down_succssor_vertex,open_List) == False):
                        if(isVisited(south_down_succssor_vertex,visited) == False):
                            open_List.append(south_down_succssor_vertex)

        # east successor
        east_succssor_row = q.row 
        east_succssor_col = q.col + 1
        east_succssor_layer = q.layer
        # check if in boundary(graph) and its not an obstacle
        if(isValid(east_succssor_layer,east_succssor_row,east_succssor_col,graph)):
            h = heuristic((q.x+1),q.y,q.z,d_x,d_y,d_z)
            east_succssor_vertex = Vertex((q.x+1),q.y,q.z,east_succssor_layer,east_succssor_row,east_succssor_col,q,(q.g+1),h,"East")
            if(isDestination(east_succssor_vertex.x,east_succssor_vertex.y,east_succssor_vertex.z,d_x,d_y,d_z) == True):
                # We find the destinaton, append q and this vertex to visited list and return
                visited.append(q)
                visited.append(east_succssor_vertex)
                return visited
            else:
                if(isInOpenList(east_succssor_vertex,open_List) == False):
                    if(isVisited(east_succssor_vertex,visited) == False):
                        open_List.append(east_succssor_vertex)
        # if the succssor is not valid, it's either (a non-air block) or (the block underneath it is an air block)  
        else:
            # up
            east_up_succssor_row = east_succssor_row
            east_up_succssor_col = east_succssor_col
            east_up_succssor_layer = east_succssor_layer + 1
            if(isValid(east_up_succssor_layer,east_up_succssor_row,east_up_succssor_col,graph)):
                h = heuristic((q.x+1),(q.y+1),q.z,d_x,d_y,d_z)
                east_up_succssor_vertex = Vertex((q.x+1),(q.y+1),q.z,east_up_succssor_layer,east_up_succssor_row,east_up_succssor_col,q,(q.g+2),h,"East_Up")
                if(isDestination(east_up_succssor_vertex.x,east_up_succssor_vertex.y,east_up_succssor_vertex.z,d_x,d_y,d_z) == True):
                    # We find the destinaton, append q and this vertex to visited list and return
                    visited.append(q)
                    visited.append(east_up_succssor_vertex)
                    return visited
                else:
                    if(isInOpenList(east_up_succssor_vertex,open_List) == False):
                        if(isVisited(east_up_succssor_vertex,visited) == False):
                            open_List.append(east_up_succssor_vertex)
            #down
            east_down_succssor_row = east_succssor_row
            east_down_succssor_col = east_succssor_col
            east_down_succssor_layer = east_succssor_layer - 1
            if(isValid(east_down_succssor_layer,east_down_succssor_row,east_down_succssor_col,graph)):
                h = heuristic((q.x+1),(q.y-1),q.z,d_x,d_y,d_z)
                east_down_succssor_vertex = Vertex((q.x+1),(q.y-1),q.z,east_down_succssor_layer,east_down_succssor_row,east_down_succssor_col,q,(q.g+2),h,"East_Down")
                if(isDestination(east_down_succssor_vertex.x,east_down_succssor_vertex.y,east_down_succssor_vertex.z,d_x,d_y,d_z) == True):
                    # We find the destinaton, append q and this vertex to visited list and return
                    visited.append(q)
                    visited.append(east_down_succssor_vertex)
                    return visited
                else:
                    if(isInOpenList(east_down_succssor_vertex,open_List) == False):
                        if(isVisited(east_down_succssor_vertex,visited) == False):
                            open_List.append(east_down_succssor_vertex)


        # west successor
        west_succssor_row = q.row 
        west_succssor_col = q.col - 1
        west_succssor_layer = q.layer
        # check if in boundary(graph) and its not an obstacle
        if(isValid(west_succssor_layer,west_succssor_row,west_succssor_col,graph)):    
            h = heuristic((q.x-1),q.y,q.z,d_x,d_y,d_z)
            west_succssor_vertex = Vertex((q.x-1),q.y,q.z,west_succssor_layer,west_succssor_row,west_succssor_col,q,(q.g+1),h,"West")
            if(isDestination(west_succssor_vertex.x,west_succssor_vertex.y,west_succssor_vertex.z,d_x,d_y,d_z) == True):
                # We find the destinaton, append q and this vertex to visited list and return
                visited.append(q)
                visited.append(west_succssor_vertex)
                return visited
            else:
                if(isInOpenList(west_succssor_vertex,open_List) == False):
                    if(isVisited(west_succssor_vertex,visited) == False):
                        open_List.append(west_succssor_vertex)
        # if the succssor is not valid, it's either (a non-air block) or (the block underneath it is an air block)  
        else:
            # up
            west_up_succssor_row = west_succssor_row
            west_up_succssor_col = west_succssor_col
            west_up_succssor_layer = west_succssor_layer + 1
            if(isValid(west_up_succssor_layer,west_up_succssor_row,west_up_succssor_col,graph)):
                h = heuristic((q.x-1),(q.y+1),q.z,d_x,d_y,d_z)
                west_up_succssor_vertex = Vertex((q.x-1),(q.y+1),q.z,west_up_succssor_layer,west_up_succssor_row,west_up_succssor_col,q,(q.g+2),h,"West_Up")
                if(isDestination(west_up_succssor_vertex.x,west_up_succssor_vertex.y,west_up_succssor_vertex.z,d_x,d_y,d_z) == True):
                    # We find the destinaton, append q and this vertex to visited list and return
                    visited.append(q)
                    visited.append(west_up_succssor_vertex)
                    return visited
                else:
                    if(isInOpenList(west_up_succssor_vertex,open_List) == False):
                        if(isVisited(west_up_succssor_vertex,visited) == False):
                            open_List.append(west_up_succssor_vertex)
            #down
            west_down_succssor_row = west_succssor_row
            west_down_succssor_col = west_succssor_col
            west_down_succssor_layer = west_succssor_layer - 1
            if(isValid(west_down_succssor_layer,west_down_succssor_row,west_down_succssor_col,graph)):
                h = heuristic((q.x-1),(q.y-1),q.z,d_x,d_y,d_z)
                west_down_succssor_vertex = Vertex((q.x-1),(q.y-1),q.z,west_down_succssor_layer,west_down_succssor_row,west_down_succssor_col,q,(q.g+2),h,"West_Down")
                if(isDestination(west_down_succssor_vertex.x,west_down_succssor_vertex.y,west_down_succssor_vertex.z,d_x,d_y,d_z) == True):
                    # We find the destinaton, append q and this vertex to visited list and return
                    visited.append(q)
                    visited.append(west_down_succssor_vertex)
                    return visited
                else:
                    if(isInOpenList(west_down_succssor_vertex,open_List) == False):
                        if(isVisited(west_down_succssor_vertex,visited) == False):
                            open_List.append(west_down_succssor_vertex)

        # push q to the visited list                
        visited.append(q)
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
    time.sleep(0.1) #without this, the agent doesn't move
    if(v.direction == "None"):
        return
    elif(v.direction == "North" or v.direction == "North_Down"):
        agent_host.sendCommand("movenorth 1")
        agent_host.sendCommand("setYaw -180")
    elif(v.direction == "North_Up"):
        agent_host.sendCommand("jumpnorth 1")
        agent_host.sendCommand("setYaw -180")
    elif(v.direction == "South" or v.direction == "South_Down"):
        agent_host.sendCommand("movesouth 1")
        agent_host.sendCommand("setYaw 0")
    elif(v.direction == "South_Up"):
        agent_host.sendCommand("jumpsouth 1")
        agent_host.sendCommand("setYaw 0")
    elif(v.direction == "East" or v.direction == "East_Down"):
        agent_host.sendCommand("moveeast 1")
        agent_host.sendCommand("setYaw -90")
    elif(v.direction == "East_Up"):
        agent_host.sendCommand("jumpeast 1")
        agent_host.sendCommand("setYaw -90")
    elif(v.direction == "West" or v.direction == "West_Down"):
        agent_host.sendCommand("movewest 1")
        agent_host.sendCommand("setYaw 90")
    elif(v.direction == "West_Up"):
        agent_host.sendCommand("jumpwest 1")
        agent_host.sendCommand("setYaw 90")

    return 

def bruteForce(agent_host,entityName):
    world_state = agent_host.getWorldState()
    loopCount =0
    while(world_state.is_mission_running == True):
        entity_location = find_entity_location(agent_host,entityName)
        agent_location = find_agent_location(agent_host)
        if entity_location is None:
            print("There is no " +entityName+ " nearby the agent")
            return
        if agent_location is None:
            return

        target_x,target_y,target_z = entity_location[0],entity_location[1],entity_location[2]
        current_x, current_y, current_z = agent_location[0],agent_location[1],agent_location[2]

        # check to keep agent positioned correctly before a discrete move command
        if current_x % 1 != 0.5:
            agent_host.sendCommand(f"tpx {math.floor (current_x) + 0.5}")
        if current_z % 1 != 0.5:
            agent_host.sendCommand(f"tpz {math.floor (current_z) + 0.5}")

        dx = target_x - current_x
        dy = target_y - current_y
        dz = target_z - current_z
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)
        yaw = -math.atan2(dx, dz) * 180 / math.pi
        pitch = math.atan2(dy, distance)
        pitch_degrees = math.degrees(pitch)

        if distance <= 1:
            agent_host.sendCommand("strafe 0")
            agent_host.sendCommand(f"setYaw {yaw}")
            agent_host.sendCommand(f"setPitch {pitch_degrees}")
            print("\nAlready at "+ entityName+"'s location.")
            return 

        else:
            if(loopCount == 0):
                print("\nMoving towards "+ entityName+"'s location...",end="")
            else:
                print(".",end="")
            if(dx>0):
                agent_host.sendCommand(f"setYaw {yaw}")
                agent_host.sendCommand(f"setPitch {pitch_degrees}")
                agent_host.sendCommand("moveeast 1")
            elif(dx<0):
                agent_host.sendCommand(f"setYaw {yaw}")
                agent_host.sendCommand(f"setPitch {pitch_degrees}")
                agent_host.sendCommand("movewest 1")
            elif(dx == 0):
                agent_host.sendCommand("strafe 0")

            if(dz>0):
                agent_host.sendCommand(f"setYaw {yaw}")
                agent_host.sendCommand(f"setPitch {pitch_degrees}")
                agent_host.sendCommand("movesouth 1")
            elif(dz<0):
                agent_host.sendCommand(f"setYaw {yaw}")
                agent_host.sendCommand(f"setPitch {pitch_degrees}")
                agent_host.sendCommand("movenorth 1")
            elif(dz==0):
                agent_host.sendCommand("strafe 0")
        world_state = agent_host.getWorldState()
        loopCount+=1

def bfs(agent_host,agent_location, target_location):
    graph,center_x,center_y = create_Graph(agent_host)
    open_List = []
    visited =[]
    # start and destination coordinates 
    s_x,s_y,s_z = agent_location[0],agent_location[1],agent_location[2]
    d_x,d_y,d_z = target_location[0],target_location[1],target_location[2]
    if(DEBUG):
        print(s_x,s_y,s_z)
    # check if the destination is on the graph
    if(isOnGraph(s_x,s_y,s_z,d_x,d_y,d_z) == False):
        return visited
    start_vertex = Vertex(s_x,s_y,s_z,center_x,center_y,None,0,0,"None")
    
    open_List.append(start_vertex)
    count = 0
    while(len(open_List)>0):
        
        q = open_List[0]
        open_List.pop(0)
        if(DEBUG):
            print("=====================================================")
            print("loop count is: ",count)
            print("Size of open List is:",len(open_List))
            print("q.x = ",q.x,"; q.y = ",q.y,"; q.z = ",q.z,"; q.parent =",q.parent,"; direction is ",q.direction)
            print("q.row = ",q.row,"; q.col = ",q.col)
        # create 4 successors
        # north succssor
        north_succssor_row = q.row - 1
        north_succssor_col = q.col

        # check if in boundary(graph) and its not an obstacle
        if(isInBoudary(north_succssor_row,north_succssor_col)):
            if(graph[north_succssor_row][north_succssor_col] == 'air'):
                north_succssor_vertex = Vertex(q.x,q.y,(q.z-1),north_succssor_row,north_succssor_col,q,0,0,"North")
                if(isVisited(north_succssor_vertex,visited) == False):
                    open_List.append(north_succssor_vertex)
                if(isDestination(north_succssor_vertex.x,north_succssor_vertex.y,north_succssor_vertex.z,d_x,d_y,d_z) == True):
                    # We find the destinaton, append q and this vertex to visited list and return
                    visited.append(q)
                    visited.append(north_succssor_vertex)
                    return visited
                
        # south successor
        south_succssor_row = q.row + 1
        south_succssor_col = q.col
        
        # check if in boundary(graph) and its not an obstacle
        if(isInBoudary(south_succssor_row,south_succssor_col)):
            if(graph[south_succssor_row][south_succssor_col] == 'air'):
                south_succssor_vertex = Vertex(q.x,q.y,(q.z+1),south_succssor_row,south_succssor_col,q,0,0,"South")
                if(isVisited(south_succssor_vertex,visited) == False):
                    open_List.append(south_succssor_vertex)
                if(isDestination(south_succssor_vertex.x,south_succssor_vertex.y,south_succssor_vertex.z,d_x,d_y,d_z) == True):
                    # We find the destinaton, append q and this vertex to visited list and return
                    visited.append(q)
                    visited.append(south_succssor_vertex)
                    return visited

        # east successor
        east_succssor_row = q.row 
        east_succssor_col = q.col + 1
        
        # check if in boundary(graph) and its not an obstacle
        if(isInBoudary(east_succssor_row,east_succssor_col)):
            if(graph[east_succssor_row][east_succssor_col] == 'air'):
                east_succssor_vertex = Vertex((q.x+1),q.y,q.z,east_succssor_row,east_succssor_col,q,0,0,"East")
                if(isVisited(east_succssor_vertex,visited) == False):
                    open_List.append(east_succssor_vertex)
                if(isDestination(east_succssor_vertex.x,east_succssor_vertex.y,east_succssor_vertex.z,d_x,d_y,d_z) == True):
                    # We find the destinaton, append q and this vertex to visited list and return
                    visited.append(q)
                    visited.append(east_succssor_vertex)
                    return visited
        # west successor
        west_succssor_row = q.row 
        west_succssor_col = q.col - 1
        
        # check if in boundary(graph) and its not an obstacle
        if(isInBoudary(west_succssor_row,west_succssor_col)):
            if(graph[west_succssor_row][west_succssor_col] == 'air'):
                west_succssor_vertex = Vertex((q.x-1),q.y,q.z,west_succssor_row,west_succssor_col,q,0,0,"West")
                if(isVisited(west_succssor_vertex,visited) == False):
                    open_List.append(west_succssor_vertex)
                if(isDestination(west_succssor_vertex.x,west_succssor_vertex.y,west_succssor_vertex.z,d_x,d_y,d_z) == True):
                    # We find the destinaton, append q and this vertex to visited list and return
                    visited.append(q)
                    visited.append(west_succssor_vertex)
                    return visited
        # push q to the visited list                
        visited.append(q)
        count+=1
    #end of while
    return visited

##########################################################

def find_nearest_trees (agent_host):
    """
    Returns a dict of tree locations and distance pairs (x, z : distance)
    sorted by increasing distance
    """

    graph, center_layer, center_row, center_col = create_Graph (agent_host)
    ind = np.argwhere(graph[center_layer:, :, :] == "log")

    agent_location = find_agent_location (agent_host)
    if agent_location is None:
        return

    current_x, current_y, current_z = agent_location[0], agent_location[1], agent_location[2]
    trees = {}
    for coords in ind:
        target_x = coords[2] - center_col
        target_y = 5
        target_z = coords[1] - center_row
        dx = target_x - current_x
        dy = target_y - current_y
        dz = target_z - current_z
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)
        trees[(target_x, target_z)] = distance    
    
    sorted_trees = sorted (trees.items(), key = lambda x:x[1])
    return sorted_trees

def find_nearest_tree (agent_host):
    """
    Finds nearest trees and moves the agents towards it
    """

    trees = find_nearest_trees (agent_host)
    if len (trees) == 0:
        return
    print (trees)
    coords, distance = trees[0]
    (x, z) = coords
    # steve height
    y = 5
    move_to_location (agent_host, [x, y, z], 0)


def find_nearest_entity_locations (agent_host, entityName):
    """
    Returns dict of entityID distance pairs (entityID : distance)
    sorted by increasing distance
    """

    world_state = agent_host.getWorldState()
    while world_state.number_of_observations_since_last_state == 0:
        time.sleep(0.1)
        world_state = agent_host.getWorldState()
        if world_state.is_mission_running == False:
            return None
    msg = world_state.observations[-1].text
    observations = json.loads(msg)

    agent_location = find_agent_location (agent_host)
    if agent_location is None:
        return

    current_x, current_y, current_z = agent_location[0], agent_location[1], agent_location[2]
    if 'entities' in observations:
        entities = {}
        for entity in observations['entities']:
            if entity['name'] == entityName:
                target_x = entity['x']
                target_y = entity['y']
                target_z = entity['z']
                entity_id = entity['id']
                
                dx = target_x - current_x
                dy = target_y - current_y + 1
                dz = target_z - current_z
                distance = math.sqrt(dx * dx + dy * dy + dz * dz)
                entities[entity_id] = distance
    
    sorted_entities = sorted (entities.items(), key = lambda x:x[1])
    return sorted_entities

def find_entity_location(agent_host,entityName):
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
            if entity['name'] == entityName:
                return (entity['x'], entity['y'], entity['z'])
    return None

def find_entityID_location(agent_host,entityID):
    """
    Finds entity with entityID and returns its coordinates (x, y, z) 
    """
    
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
            if entity['id'] == entityID:
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
                return (entity['x'], entity['y'], entity['z'], entity['yaw'])
    return None

def move_to(agent_host,entityName,mode):
    entity_location = find_entity_location(agent_host,entityName)
    agent_location = find_agent_location(agent_host)
    if entity_location is None:
        print("There is no " +entityName+ " nearby the agent")
        return
    if agent_location is None:
        return
    #Use Astar
    if(mode == 0):
        visited_nodes = Astar_search(agent_host,agent_location,entity_location)
        path = traceThePath(visited_nodes,entity_location[0],entity_location[1],entity_location[2])
        if(len(path) == 0):
            print("No path Found")
            return
        for v in path:
            print(v.x,v.y,v.z,v.direction)
            movement(agent_host,v)
    #Use bfs
    if(mode == 1):
        visited_nodes = bfs(agent_host,agent_location,entity_location)
        path = traceThePath(visited_nodes,entity_location[0],entity_location[1],entity_location[2])
        if(len(path) == 0):
            print("No path Found")
            return
        for v in path:
            print(v.x,v.y,v.z,v.direction)
            movement(agent_host,v)
    #Use Brute Force
    elif(mode == 2):
        bruteForce(agent_host,entityName)

    return 

def move_to_location (agent_host, location, mode):
    """
    Moves agent to location's coordinates location = (x, y, z)
    """
    
    agent_location = find_agent_location(agent_host)
    
    if agent_location is None:
        return
    
    #Use Astar
    if(mode == 0):
        visited_nodes = Astar_search(agent_host, agent_location, location)
        path = traceThePath(visited_nodes, location[0], location[1], location[2])
        if(len(path) == 0):
            print("No path Found")
            return
        for v in path:
            print(v.x,v.y,v.z,v.direction)
            movement(agent_host,v)
    #Use bfs
    if(mode == 1):
        visited_nodes = bfs(agent_host, agent_location, location)
        path = traceThePath(visited_nodes, location[0], location[1], location[2])
        if(len(path) == 0):
            print("No path Found")
            return
        for v in path:
            print(v.x,v.y,v.z,v.direction)
            movement(agent_host,v)
    #Use Brute Force
    # elif(mode == 2):
    #     bruteForce(agent_host,entityName)

    return 

def chase_entity (agent_host, entityName, entityID):
    """
    Makes the agent chase and attack an entity with entityID
    """

    world_state = agent_host.getWorldState()
    if world_state.number_of_observations_since_last_state > 0:
        msg = world_state.observations[-1].text
        observations = json.loads(msg)
        
        entity_location = find_entityID_location (agent_host, entityID)
        agent_location = find_agent_location (agent_host)
        
        if entity_location is None:
            print("There is no " + entityName + " nearby the agent")
            return
        if agent_location is None:
            return

        target_x, target_y, target_z = entity_location[0], entity_location[1], entity_location[2]
        current_x, current_y, current_z, current_yaw = agent_location[0], agent_location[1], agent_location[2], agent_location[3]
        
        # check to keep agent positioned correctly before a discrete move command
        if current_x % 1 != 0.5:
            agent_host.sendCommand(f"tpx {math.floor (current_x) + 0.5}")
        if current_z % 1 != 0.5:
            agent_host.sendCommand(f"tpz {math.floor (current_z) + 0.5}")

        dx = target_x - current_x
        dy = target_y - current_y + 1
        dz = target_z - current_z
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)
        yaw = -math.atan2(dx, dz) * 180 / math.pi
        pitch = math.atan2(dy, distance)
        pitch_degrees = math.degrees(pitch)

        difference = yaw - current_yaw;
        while difference < -180:
            difference += 360
        while difference > 180:
            difference -= 360
        difference /= 180.0

        agent_host.sendCommand("turn " + str(difference))
        
        if distance <= 1:
            agent_host.sendCommand("move -1")
        if distance <= 3:
            # Use the line-of-sight observation to determine when to hit and when not to hit:
            if "LineOfSight" in observations:
                los = observations[u'LineOfSight']
                type = los["type"]
                if type == entityName:
                    agent_host.sendCommand("attack 1")
                    print ("attack")
                    agent_host.sendCommand("attack 0")
            agent_host.sendCommand(f"setPitch {pitch_degrees}")        
            print("\nAlready at "+ entityName+"'s location.")
        
        dx = math.floor (dx)
        dz = math.floor (dz)
        if(dx>0):
            agent_host.sendCommand(f"setPitch {pitch_degrees}")
            agent_host.sendCommand("moveeast 1")
        elif(dx<0):
            agent_host.sendCommand(f"setPitch {pitch_degrees}")
            agent_host.sendCommand("movewest 1")
        elif(dx == 0):
            agent_host.sendCommand("strafe 0")
        
        if(dz>0):
            agent_host.sendCommand(f"setPitch {pitch_degrees}")
            agent_host.sendCommand("movesouth 1")
        elif(dz<0):
            agent_host.sendCommand(f"setPitch {pitch_degrees}")
            agent_host.sendCommand("movenorth 1")
        elif(dz==0):
            agent_host.sendCommand("strafe 0")

        world_state = agent_host.getWorldState()