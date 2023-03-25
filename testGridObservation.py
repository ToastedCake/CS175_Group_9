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
import Astar_bfs_bruteForce as find
import nlp_parser as nlp
import numpy as np

obs_x_range = 100
obs_y_range = 1
obs_z_range = 100

if sys.version_info[0] == 2:
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately
else:
    import functools
    print = functools.partial(print, flush=True)
    

def serObservationRange():
    """Set the observation range for the agent."""
    s = ""
    s += '<Range name="entities" xrange="' + str(obs_x_range)+'" yrange="' +str(obs_y_range)+ '" zrange="'+str(obs_z_range) +'"/>'
    return s

def getBlockDrawing():
    """Create the XML for the entities."""
    s = ""
    s+=  '<DrawBlock x="0" y="4" z="0" type="diamond_block" />'
    
    return s

def getItemDrawing():
    """Create the XML for the items."""
    s = ""
    s += '<DrawItem x="0" y="5" z="20" type="diamond_sword"/>'
    # s += '<DrawItem x="0" y="5" z="20" type="diamond_axe"/>'
    return s

def getEntityDrawing():
    """Create the XML for the entities."""
    s = ""
    s += '<DrawEntity x="10" y="5" z="10" type="Pig"/>'
    # s += '<DrawEntity x="10" y="5" z="10" type="Cow"/>'
    # s += '<DrawEntity x="10" y="5" z="10" type="Sheep"/>'
    return s

def getMissionXML():

    return '''
    <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <About>
            <Summary>Recognize Speech Commands</Summary>
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
                <FlatWorldGenerator generatorString="3;7,3*3,2;131;biome_1(distance=10),village,decoration,dungeon"/>
                <DrawingDecorator>
                    '''+ getItemDrawing() + getBlockDrawing()+getEntityDrawing()+'''
                </DrawingDecorator>
                <ServerQuitFromTimeUp timeLimitMs="100000"/>
                <ServerQuitWhenAnyAgentFinishes />
            </ServerHandlers>
        </ServerSection>
        <AgentSection mode="Survival">
            <Name>Agent</Name>
            <AgentStart>
                <Placement x="0.5" y="5" z="0.5"/>
            </AgentStart>
            <AgentHandlers>
                <ObservationFromRay/>
                <ObservationFromNearbyEntities>
                    ''' + serObservationRange() + '''
                </ObservationFromNearbyEntities>
                <ChatCommands/>
                <ObservationFromGrid>                      
                <Grid name="grid_observation">                        
                <min x="-59" y="-2" z="-59"/>                        
                <max x="59" y="3" z="59"/>                    
                </Grid>                  
                </ObservationFromGrid>
                <DiscreteMovementCommands>
                    <ModifierList type="deny-list">
                        <command>attack</command>
                        <command>turn</command>
                    </ModifierList>
                </DiscreteMovementCommands>
                <AbsoluteMovementCommands/>
                <ContinuousMovementCommands turnSpeedDegs="620">
                    <ModifierList type="allow-list">
                        <command>attack</command>
                        <command>turn</command>
                    </ModifierList>
                </ContinuousMovementCommands>
                <ObservationFromFullInventory flat="false"/>
                <InventoryCommands/>
                <MissionQuitCommands/>
            </AgentHandlers>
        </AgentSection>
    </Mission>'''

missionXML= getMissionXML()


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
print("Mission running", end='')
#################################################

start_time = time.time()

nlp.parse_speech_command (agent_host = agent_host)

end_time = time.time() - start_time

print ("time executed: ", end_time)

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