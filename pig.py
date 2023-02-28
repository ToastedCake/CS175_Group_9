
from __future__ import print_function
# ------------------------------------------------------------------------------------------------
# Copyright (c) 2016 Microsoft Corporation
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
# associated documentation files (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge, publish, distribute,
# sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or
# substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
# NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# ------------------------------------------------------------------------------------------------

# Tutorial sample #2: Run simple mission using raw XML

from builtins import range
import json
import MalmoPython
import os
import sys
import time
import math

if sys.version_info[0] == 2:
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately
else:
    import functools
    print = functools.partial(print, flush=True)

# More interesting generator string: "3;7,44*49,73,35:1,159:4,95:13,35:13,159:11,95:10,159:14,159:6,35:6,95:6;12;"
                    # <DrawLine x1="-1" y1="5" z1="-1" x2="-1" y2="5" z2="4" type="fence"/>
                    # <DrawLine x1="0" y1="5" z1="-1" x2="3" y2="5" z2="-1" type="fence"/>
                    # <DrawLine x1="4" y1="5" z1="-1" x2="4" y2="5" z2="4" type="fence"/>
                    # <DrawLine x1="0" y1="5" z1="4" x2="3" y2="5" z2="4" type="fence"/>
missionXML="""
    <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <About>
            <Summary>Find the pig and move towards it.</Summary>
        </About>

        <ServerSection>
            <ServerInitialConditions>
                <Time>
                    <StartTime>1000</StartTime>
                    <AllowPassageOfTime>false</AllowPassageOfTime>
                </Time>
                <Weather>clear</Weather>
            </ServerInitialConditions>
            <ServerHandlers>
                <FlatWorldGenerator generatorString="3;7,3*3,2;12;biome_1,village"/>
                <DrawingDecorator>
                    <DrawEntity x="0.5" y="5" z="0.5" type="Pig"/>
                </DrawingDecorator>
                <ServerQuitFromTimeUp timeLimitMs="10000"/>
                <ServerQuitWhenAnyAgentFinishes />
            </ServerHandlers>
        </ServerSection>
        <AgentSection mode="Survival">
            <Name>Agent</Name>
            <AgentStart>
                <Placement x="16.5" y="5" z="-10.5"/>
            </AgentStart>
            <AgentHandlers>
                <ObservationFromNearbyEntities>
                    <Range name="entities" xrange="30" yrange="30" zrange="30"/>
                </ObservationFromNearbyEntities>
                <DiscreteMovementCommands/>
                <AbsoluteMovementCommands/>
                <InventoryCommands/>
                <MissionQuitCommands/>
            </AgentHandlers>
        </AgentSection>
    </Mission>
"""

def find_pig_location(agent_host):
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
            if entity['name'] == 'Pig':
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

def move_to(agent_host):       
    while(1):
        # time.sleep(2)
        # msg = world_state.observations[-1].text
        # observations = json.loads(msg)
        # print(observations)
        pig_location = find_pig_location(agent_host)
        agent_location = find_agent_location(agent_host)
        if pig_location is None:
            print("There is no pig nearby the agent")
            return
        if agent_location is None:
            return
        
        target_x,target_y,target_z = pig_location[0],pig_location[1],pig_location[2]
        current_x, current_y, current_z = agent_location[0],agent_location[1],agent_location[2]

        dx = target_x - current_x
        dy = target_y - current_y
        dz = target_z - current_z
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)
        yaw = -math.atan2(dx, dz) * 180 / math.pi
        # print("agent location: (",current_x,current_y,current_z,")\n")
        # print("pigs location: (",target_x,target_y,target_z,")\n")
        # print("dx,dy,dz,distance are: (",dx,dy,dz,distance,")\n")

        if distance == 0:
            agent_host.sendCommand("strafe 0")
            print("Already at target location.")
            return 

        else:
            print("Moving towards target location...")
            if(dx>0):
                agent_host.sendCommand(f"setYaw {yaw}")
                agent_host.sendCommand("moveeast 1")
            elif(dx<0):
                agent_host.sendCommand(f"setYaw {yaw}")
                agent_host.sendCommand("movewest 1")
            elif(dx == 0):
                agent_host.sendCommand("strafe 0")

            if(dz>0):
                agent_host.sendCommand(f"setYaw {yaw}")
                agent_host.sendCommand("movesouth 1")
            elif(dz<0):
                agent_host.sendCommand(f"setYaw {yaw}")
                agent_host.sendCommand("movenorth 1")
            elif(dz==0):
                agent_host.sendCommand("strafe 0")

# Create default Malmo objects:
agent_host = MalmoPython.AgentHost()
try:
    agent_host.parse( sys.argv )
except RuntimeError as e:
    print('ERROR:',e)
    print(agent_host.getUsage())
    exit(1)
if agent_host.receivedArgument("help"):
    print(agent_host.getUsage())
    exit(0)

my_mission = MalmoPython.MissionSpec(missionXML, True)
my_mission_record = MalmoPython.MissionRecordSpec()

# Attempt to start a mission:
max_retries = 3
for retry in range(max_retries):
    try:
        agent_host.startMission( my_mission, my_mission_record )
        break
    except RuntimeError as e:
        if retry == max_retries - 1:
            print("Error starting mission:",e)
            exit(1)
        else:
            time.sleep(2)

# Loop until mission starts:
print("Waiting for the mission to start ", end=' ')
world_state = agent_host.getWorldState()
while not world_state.has_mission_begun:
    print(".", end="")
    time.sleep(0.1)
    world_state = agent_host.getWorldState()
    for error in world_state.errors:
        print("Error:",error.text)

print()
print("Mission running ", end=' ')
#################################################
# Find the pig's location on the map and move the agent toward it
move_to(agent_host)



######################################################
# Loop until mission ends:
while world_state.is_mission_running:
    print(".", end="")
    time.sleep(0.1)
    world_state = agent_host.getWorldState()
    for error in world_state.errors:
        print("Error:",error.text)

print()
print("Mission ended")
# Mission has ended.
