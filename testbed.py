import time
import json
import random
import MalmoPython

# Spawn `num_mobs` `mob_type`s within `distance` of agent's location (x, y, z)
def spawn_mobs(mob_type, num_mobs, agent_host, x, y, z, distance=10):
    # Randomize x and z to be within "distance" of agent
    for i in range(num_mobs):
        mob_x = random.randint(int(x - distance), int(x + distance))
        mob_z = random.randint(int(z - distance), int(z + distance))
        agent_host.sendCommand(f"chat /summon {mob_type} {mob_x} {y} {mob_z}")

    # Wait for mobs to spawn
    time.sleep(1)

def run_mission(mob_type, num_mobs):
    # Define starting position for agent
    x = 0
    y = 5.0
    z = 0
    yaw = 0

    mission_xml = f'''
        <?xml version="1.0" encoding="UTF-8" standalone="no" ?>
        <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        
        <About>
            <Summary>Create testbed for agent behavior</Summary>
        </About>
        
        <ServerSection>
            <ServerInitialConditions>
                <Time>
                    <StartTime>12000</StartTime>
                    <AllowPassageOfTime>false</AllowPassageOfTime>
                </Time>
                <AllowSpawning>true</AllowSpawning>
                <AllowedMobs>{mob_type}</AllowedMobs>
            </ServerInitialConditions>
            <ServerHandlers>
                <FlatWorldGenerator generatorString="3;7,2x3,2;1;"/>
                <ServerQuitFromTimeUp timeLimitMs="5000"/>
                <ServerQuitWhenAnyAgentFinishes/>
            </ServerHandlers>
        </ServerSection>
        
        <AgentSection mode="Survival">
            <Name>MalmoTutorialBot</Name>
            <AgentStart>
                <Placement x="{x}" y="{y}" z="{z}" yaw="{yaw}"/>
            </AgentStart>
            <AgentHandlers>
                <ChatCommands/>
                <ObservationFromFullStats/>
                <ContinuousMovementCommands turnSpeedDegs="180"/>
            </AgentHandlers>
        </AgentSection>
        </Mission>'''

    # Set up agent host
    agent_host = MalmoPython.AgentHost()
    agent_host.setObservationsPolicy(MalmoPython.ObservationsPolicy.LATEST_OBSERVATION_ONLY)

    # Load mission
    mission = MalmoPython.MissionSpec(mission_xml, True)
    mission_record = MalmoPython.MissionRecordSpec()

    # Attempt to start a mission:
    max_retries = 3
    for retry in range(max_retries):
        try:
            agent_host.startMission(mission, mission_record)
            break
        except RuntimeError as e:
            if retry == max_retries - 1:
                print("Error starting mission:", e)
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

    # Spawn mobs
    spawn_mobs(mob_type, num_mobs, agent_host, x, y, z)

    # Main loop
    while world_state.is_mission_running:
        world_state = agent_host.getWorldState()

        if world_state.number_of_observations_since_last_state > 0:
            msg = world_state.observations[-1].text
            observations = json.loads(msg)
            
            # EXAMPLE: print location of agent
            # x = observations["XPos"]
            # y = observations["YPos"]
            # z = observations["ZPos"]
            # print(f"Agent is at ({x}, {y}, {z})")

        # if world_state.number_of_rewards_since_last_state > 0:
        #     reward = world_state.rewards[-1]

    # End mission
    time.sleep(1)
    agent_host.sendCommand("quit")
    time.sleep(1)

if __name__ == "__main__":
    # Specify the mob type and number of mobs to spawn
    mob_type = "Cow"
    num_mobs = 5

    # Run the mission
    run_mission(mob_type, num_mobs)
