import sys
import json
import random
import time
import math
from collections import deque
from timeit import default_timer as timer

"""
CREDIT: The code for the following functions were either 
    partially or completely pulled from assignment2.py.
    
- update_q_table
- choose_action

CREDIT: Part of the inspiration for the load_grid function came from the
    following github repository: github.com/ctypewriter/Poro-Pathfinder

TODO s:
1, replace generator string for flat world generator

"""

SPEED = 0.45
GOAL_REWARD = 5000
GOAL_TYPE = 'diamond_block'

missionXML = f'''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
            <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            
                <About>
                <Summary>Get to the goal!</Summary>
                </About>
                
                <ModSettings>
                <MsPerTick> 25 </MsPerTick>
                </ModSettings>
                
                <ServerSection>
                    <ServerInitialConditions>
                        <Time>
                            <StartTime>12000</StartTime>
                            <AllowPassageOfTime>false</AllowPassageOfTime>
                        </Time>
                        <Weather>clear</Weather>
                    </ServerInitialConditions>
                    <ServerHandlers>
                        <FlatWorldGenerator generatorString="3;7,3*3;1;village"/>
                        <ServerQuitWhenAnyAgentFinishes/>
                    </ServerHandlers>
                </ServerSection>
                
                <AgentSection mode="Survival">
                    <AgentStart>
                        <Placement x=".5" y="4" z=".5"/>
                    </AgentStart>

                    <AgentHandlers>
                        <ObservationFromFullStats/>
                        <ContinuousMovementCommands turnSpeedDegs="180"/>
                        <MissionQuitCommands/>
                        
                        <RewardForTouchingBlockType>
                            <Block reward="{GOAL_REWARD}" type="{GOAL_TYPE}" behaviour="onceOnly"/>
                        </RewardForTouchingBlockType>

                        <ObservationFromGrid>
                            <Grid name="floor">
                                <min x="-1" y="-1" z="-1"/>
                                <max x="1" y="-1" z="1"/>
                            </Grid>
                            <Grid name="level1">
                                <min x="-1" y="0" z="-1"/>
                                <max x="1" y="0" z="1"/>
                            </Grid>
                            <Grid name="level2">
                                <min x="-1" y="1" z="-1"/>
                                <max x="1" y="1" z="1"/>
                            </Grid>
                        </ObservationFromGrid>
                        
                        <AgentQuitFromTouchingBlockType>
                            <Block type="diamond_block"/>
                        </AgentQuitFromTouchingBlockType>
                        
                    </AgentHandlers>
                </AgentSection>
            </Mission>'''

# get distance between two 3d points
def distance(x, y, z, x2, y2, z2):
    return math.sqrt(math.fabs(x - x2) ** 2 + math.fabs(y - y2) ** 2 + math.fabs(z - z2) ** 2)

class Agent(object):
    # initializes agent
    def __init__(self, goal_x, goal_y, goal_z, alpha=0.3, gamma=1, n=2):
        """Constructing an RL agent.

        Args
            alpha:  <float>  learning rate      (default = 0.3)
            gamma:  <float>  value decay rate   (default = 1)
            n:      <int>    number of back steps to update (default = 1)
        """
        self.epsilon = 0.2  # chance of taking a random action instead of the best
        self.q_table = {}
        self.n, self.alpha, self.gamma = n, alpha, gamma
        self.x, self.y, self.z = 0, 0, 0                    # agent's position
        self.goal_x, self.goal_y, self.goal_z = goal_x, goal_y, goal_z

    # fetches a 3D grid of observations around agent
    def get_grid_and_observations(self, agent_host, world_state):
        grid = dict()
        observations = None
        while world_state.is_mission_running:
            world_state = agent_host.getWorldState()
            if len(world_state.errors) > 0:
                raise AssertionError('get_grid() failed.')

            if world_state.number_of_observations_since_last_state > 0:
                msg = world_state.observations[-1].text
                observations = json.loads(msg)
                grid[0] = observations.get(u'floor', 0)
                grid[1] = observations.get(u'level1', 0)
                grid[2] = observations.get(u'level2', 0)
                break
        return grid, observations

    # returns all possible actions that can be done at the current state
    def get_possible_actions(self, S):
        action_list = []

        # get current state [N, W, E, S, goal orientation, yaw]
        s = S[-1]

        dirs = ['N', 'W', 'E', 'S']
        for i in range(4):
            if s[i] == 'down' or s[i] == 'flat':
                action_word = 'move'
                if i == 1 or i == 2:
                    action_word = 'strafe'
                if i == 1 or i == 3:
                    action_list.append(f'{action_word} -{SPEED}')
                else:
                    action_list.append(f'{action_word} {SPEED}')
            elif s[i] == 'hill':
                action_list.append(f'jump {dirs[i]}')

        return action_list
    
    # returns the direction that the agent should travel to reach goal
    def goal_orientation(self, current_x, current_z):
        if math.fabs(current_z - self.z) >= math.fabs(current_x - self.x):
            return 'S' if current_z > self.z else 'N'
        return 'E' if current_x > self.x else 'W'

    # returns the type of terrain the agent is approaching
    def terrain_type(self, floor, level1, level2):
        if floor == u'air' and level1 == u'air' and level2 == u'air':
            return 'down'
        elif floor != u'air' and level1 == u'air' and level2 == u'air':
            return 'flat'
        elif floor != u'air' and level2 != u'air':
            return 'obstacle'
        elif level1 != u'air' and level2 == u'air':
            return 'hill'
        return 'unknown'

    # returns position and yaw of the agent
    def get_position_and_yaw(self, observations):
        self.x = observations.get(u'XPos', 0)
        self.y = observations.get(u'YPos', 0)
        self.z = observations.get(u'ZPos', 0)
        return tuple((math.floor(self.x), math.floor(self.y), math.floor(self.z), observations.get(u'Yaw', 0)))

    # returns state [terrain N, terrain W, terrain E, terrain S, goal orientation, yaw]
    def get_curr_state(self, agent_host):
        """Creates a unique identifier for a state."""

        world_state = agent_host.getWorldState()
        grid, observations = self.get_grid_and_observations(agent_host, world_state)
        position = self.get_position_and_yaw(observations)
        state = [None for i in range(6)]

        if (world_state.is_mission_running):
            for i in range(4):
                state[i] = self.terrain_type(grid[0][7-i*2], grid[1][7-i*2], grid[2][7-i*2])
            state[4] = self.goal_orientation(position[0], position[2])
            state[5] = position[3]

        return tuple(state)

    # choose best action
    def choose_action(self, curr_state, possible_actions, eps):
        """Chooses an action according to eps-greedy policy. """
        if curr_state not in self.q_table:
            self.q_table[curr_state] = {}
        for action in possible_actions:
            if action not in self.q_table[curr_state]:
                self.q_table[curr_state][action] = 0

        # choose action
        if random.random() < eps:
            # choose random action
            return random.choice(possible_actions)
        # else get q_vales for curr_state and find max_q
        q_values = self.q_table[curr_state]
        max_q = max(q_values.values())
        # get all actions with max_q and randomly select and return one
        actions_with_max_q = [a for a, q in q_values.items() if q == max_q]
        return random.choice(actions_with_max_q)
    
    # have agent perform action
    def act(self, agent_host, action):
        print(action + ",", end = " ")

        # reset movement
        self.still(agent_host)

        direction = action.split()[-1]
        if direction in ("N", "W", "E", "S"):
            if direction == "N":
                agent_host.sendCommand(f'move {SPEED}')
            elif direction == "W":
                agent_host.sendCommand(f'strafe -{SPEED}')
            elif direction == "E":
                agent_host.sendCommand(f'strafe {SPEED}')
            elif direction == "S":
                agent_host.sendCommand(f'move -{SPEED}')
            time.sleep(.25)
            agent_host.sendCommand("jump 1")
        else:
            agent_host.sendCommand(action)
        time.sleep(.05)

        # reset movement
        self.still(agent_host)

    # stills the agent / resets its movement
    @staticmethod
    def still(agent_host):
        agent_host.sendCommand("jump 0")
        agent_host.sendCommand("strafe 0")
        agent_host.sendCommand("move 0")
        
    # update the q table
    def update_q_table(self, tau, S, A, R, T):
        """Performs relevant updates for state tau.

        Args
            tau: <int>  state index to update
            S:   <dequqe>   states queue
            A:   <dequqe>   actions queue
            R:   <dequqe>   rewards queue
            T:   <int>      terminating state index
        """
        curr_s, curr_a, curr_r = S.popleft(), A.popleft(), R.popleft()
        G = sum([self.gamma ** i * R[i] for i in range(len(S))])
        if tau + self.n < T:
            G += self.gamma ** self.n * self.q_table[S[-1]][A[-1]]

        old_q = self.q_table[curr_s][curr_a]
        self.q_table[curr_s][curr_a] = old_q + self.alpha * (G - old_q)

    # run agent
    def run(self, agent_host):
        S, A, R = deque(), deque(), deque()
        reward = 0
        done_update = False

        while not done_update:
            # Get beginning state/action
            s0 = self.get_curr_state(agent_host)
            a0 = self.choose_action(s0, self.get_possible_actions(agent_host), self.epsilon)
            
            S.append(s0)
            A.append(a0)
            R.append(0)

            T = sys.maxsize
            distance0 = distance(self.x, self.y, self.z, self.goal_x, self.goal_y, self.goal_z)

            for t in range(sys.maxsize):
                time.sleep(0.1)
                if t < T:
                    self.act(agent_host, A[-1])
                    world_state = agent_host.getWorldState()

                    if not world_state.is_mission_running:
                        T += 1
                        S.append('Term State')
                        R.append(100)
                        reward = reward + 100
                    else:
                        s = self.get_curr_state(agent_host)
                        S.append(s)
                        
                        distance1 = distance(self.x, self.y, self.z, self.goal_x, self.goal_y, self.goal_z)
                        reward += distance0 - distance1
                        R.append((distance0 - distance1))
                        distance0 = distance1

                        possible_actions = self.get_possible_actions(agent_host)
                        next_a = self.choose_action(s, possible_actions, self.epsilon)
                        A.append(next_a)

                tau = t - self.n + 1
                if tau >= 0:
                    self.update_q_table(tau, S, A, R, T)

                if tau == T - 1:
                    while len(S) > 1:
                        tau = tau + 1
                        self.update_q_table(tau, S, A, R, T)
                    done_update = True
                    break

        print("Reward: ", reward)
        print("Q-table: ", self.q_table)
