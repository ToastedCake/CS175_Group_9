import spacy
from spacy.symbols import *
import numpy as np
from word2number import w2n

# Load trained nlp model
# trained_model_path = "I:\\My Drive\\UCI\\Winter 2023\\COMPSCI 175\\text_parse\\text_parse\models\\trained-trf-pos-model"
nlp = spacy.load ("en_core_web_trf")

from gensim.models import KeyedVectors
from gensim import models
from gensim.models import Word2Vec
import json
import AstarSearch
import math
import time

# Load pretrained model (since intermediate data is not included, the model cannot be refined with additional data)
#model = Word2Vec.load_word2vec_format('GoogleNews-vectors-negative300.bin', binary=True, norm_only=True) -> Deprecated

# vector_model_path = "C:\\Users\\Unkow\\Downloads\\GoogleNews-vectors-negative300.bin.gz"
# model = gensim.models.KeyedVectors.load_word2vec_format (vector_model_path, binary=True) # without *norm_only* param

# model.init_sims(replace=True)
# model.save("models/GoogleNews")

# Load saved vector model
# saved_vector_model_path = "models/GoogleNews"
saved_vector_model_path = "I:\\My Drive\\UCI\\Winter 2023\\COMPSCI 175\\text_parse\\text_parse\\models\\GoogleNews"
model = KeyedVectors.load (saved_vector_model_path, mmap='r')

import warnings
warnings.filterwarnings(action='ignore', category=UserWarning)  # suppress TracerWarning

DEBUG = False

command_map = {
            "move": {
                "stop": ["move 0", "strafe 0"],
                "forward": "move 1", "forwards": "move 1", "back": "move -1", "backward": "move -1", "backwards": "move -1", "right": "strafe 1", "left": "strafe -1",
                "north": "movenorth 1", "south": "movesouth 1", "east": "moveeast 1", "west": "movewest 1",
                "to": "OBJECT"
            },
            "strafe": {"right": "strafe 1", "left": "strafe -1", "stop": ["strafe 0"]},
            "turn": {"right": "turn 1", "left": "turn -1", "stop": ["turn 0", "pitch 0"],
                     "up": "pitch -1", "down": "pitch 1"},
            "look": {"up": "look -1", "down": "look 1"},
            "pitch": {"up": "pitch -1", "down": "pitch 1", "stop": ["pitch 0"]},
            "jump": {
                "": "jump 1", "up": "jump 1", "stop": ["jump 0"], "forward": "jumpmove 1", "back": "jumpmove -1",
                "backwards": "jumpmove -1", "right": "jumpstrafe 1", "left": "jumpstrafe -1",
                "north": "jumpnorth 1", "south": "jumpsouth 1", "east": "jumpeast 1", "west": "jumpwest 1"
            },
            "crouch": {"": "crouch 1", "stop": ["crouch 0"]},
            "attack": {"": "attack 1", "stop": ["attack 0"]},
            "use": {},
            "get": {"": "OBJECT"},
            "discard": {"": "discardCurrentItem"},
            "stop": ["move 0", "jump 0", "turn 0", "strafe 0", "pitch 0", "crouch 0", "attack 0"],
            "quit": {"": "quit"}
        }

def word_similarity_score (word1, word2):
    score = model.similarity (word1, word2)
    return score

def get_best_match (word, commands_map, threshold):
    scores = []
    for commands in commands_map:
        score = word_similarity_score (word, commands)
        scores.append (score)
    keys = list (commands_map.keys())
    command = keys[np.argmax (scores)]
    return command

def get_similar_command (verb, commands_map, agent_host):
    lemma_verb = verb.lemma_
    # synonyms?
    # left
    if verb.pos != VERB:
        return verb
    # get synonym?
    t = 0.5
    command = get_best_match (lemma_verb, commands_map, t)
    return command

def send_command (verb, commands_map, agent_host):
    if str (verb) == "stop":
        return send_stop_command (commands_map, agent_host)
    command = commands_map.get (str (verb)).get('')
    return [command]
 
def send_command_option (verb, option, commands_map, agent_host):
    for a in option.ancestors:
        if a.pos == VERB:
            for r in a.rights:
                if r.pos == NOUN:
                    return None
                elif r.lemma_ != option.lemma_:
                    break
    
    for l in option.lefts:
        if l.pos == NOUN:
            for l in l.lefts:
                if l.pos == NUM:
                    command = commands_map.get (verb).get (option.lemma_)
                    n  = w2n.word_to_num (l.lemma_)
                    commands = []
                    for i in range (n):
                        commands.append (command)
                    return commands
        else:
            break

    command = commands_map.get (verb).get (option.lemma_)
    return [command]

def send_prop_command (verb, prep, commands_map, agent_host):
    if prep.lemma_ in commands_map.get ("move"):
        for r in prep.rights:
            if r.pos_ == "NOUN":
                # move to OBJECT
                if agent_host == None:
                    return [str (verb) + " " + str (prep) + " " + str(r)]
                AstarSearch.move_to (agent_host, str (r))
                return [None]
            elif r.lemma_ in commands_map.get ("move"):
                c = send_command_option (verb, r, commands_map, agent_host)
                if c:
                    return c

def send_object_command (verb, object, commands_map, agent_host):
    for l in object.lefts:
        if l.pos == NUM:  
            for a in l.ancestors:
                if a.pos == VERB:
                    for r in a.rights:
                        if r.pos == ADV:
                            command = commands_map.get (verb).get (r.lemma_)
                            n  = w2n.word_to_num (l.lemma_)
                            commands = []
                            for i in range (n):
                                commands.append (command)
                            return commands

    if agent_host == None:
        return [str (verb) + " " + str (object)]
    
    if verb == "get":
        AstarSearch.move_to (agent_host, str (object))
        return [None]

    if verb == "use":
        world_state = agent_host.getWorldState()
        if world_state.number_of_observations_since_last_state > 0:
            msg = world_state.observations[-1].text
            observations = json.loads(msg)
            if "inventory" in observations:
                items = observations["inventory"]
                for i in items:
                    type = i["type"]
                    index = i["index"]
                    if object.text in type:
                        return ["hotbar." + str (index + 1) + " 1"]
    elif verb == "attack":
        return [str (verb) + " " + str (object)]
    elif verb == "grab":
        return [str (verb) + " " + str (object)]

def send_stop_command (commands_map, agent_host):
    command = commands_map.get ("stop")
    return command

def parse_root_verb (verb, commands_map, agent_host):
    malmo_command = get_similar_command (verb, commands_map, agent_host)
    
    if DEBUG:
        print ("malmo command: ", malmo_command)

    commands = []
    if sum (1 for r in verb.rights) == 0:
        c = send_command (malmo_command, commands_map, agent_host)
        if c:
            commands.append (c)
    
    for word in verb.rights:
        if DEBUG:
            print ("word: ", word, word.pos_)
        if word.pos == ADV:
            # move forward
            # move backwards
            if word.lemma_ in commands_map.get (malmo_command):
                c = send_command_option (malmo_command, word, commands_map, agent_host)
                if c:
                    commands.append (c)             
        elif word.pos == VERB:
            # subsequent command
            # move forward and dig
            if word.lemma_ == "stop":
                c = send_stop_command (commands_map, agent_host)
                if c:
                    commands.append (c)
            else:
                c = parse_root_verb (word, commands_map, agent_host)
                if c:
                    for c in c:
                        commands.append (c)           
        elif word.pos == ADP:
            # preposition object
            # move to the left
            # move to the right
            # move to
            c = send_prop_command (malmo_command, word, commands_map, agent_host)
            if c:
                commands.append (c)        
        elif word.pos == NOUN or word.pos == PROPN:
            # move 1 block forward
            c = send_object_command (malmo_command, word, commands_map, agent_host)
            if c:
                commands.append (c)
        elif word.pos == CCONJ:
            c = send_command (malmo_command, commands_map, agent_host)
            if c:
                commands.append (c)                

    return commands

def check_agent_pos (agent_host):
        # check to keep agent positioned correctly before a discrete move command
    agent_location = AstarSearch.find_agent_location(agent_host)
    if agent_location:
        if agent_location[0] % 1 != 0.5:
            agent_host.sendCommand(f"tpx {math.floor (agent_location[0]) + 0.5}")
        if agent_location[2] % 1 != 0.5:
            agent_host.sendCommand(f"tpz {math.floor (agent_location[2]) + 0.5}")


def parse_string_command (string, commands_map = command_map, agent_host = None):
    doc = nlp (string)
    commands = []
    for sentence in doc.sents:
            r = sentence.root
            c = parse_root_verb (r, commands_map, agent_host)
            if c:
                for c in c:
                    commands.append (c)
    
    if agent_host == None:
        return commands
    
    for c in commands:
        if c:
            print (c, len (c))
            for c in c:
                if c:
                    check_agent_pos (agent_host)
                    agent_host.sendCommand (c)
            time.sleep(1)

if __name__ == "__main__":
    command = input (": ")
    while command.lower() != "quit":
        commands = parse_string_command (command, command_map)
        
        for c in commands:
            print (c)
        
        command = input (": ")