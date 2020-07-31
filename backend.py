import json
import os
import time
import sys
import urllib.parse
import urllib.request
import hashlib

import user_config
from galaxy.api.consts import LocalGameState
from galaxy.api.types import LocalGame, GameTime
from galaxy.api.plugin import Plugin
from xml.dom import minidom
from xml.etree import ElementTree
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

def is_ePSXe_running():
    tasklist = os.popen('tasklist').read().strip().split('\n')
    for i in range(len(tasklist)):
        if 'ePSXe.exe' in tasklist[i]:
            return True
    return False

def get_the_game_times():
    file = ElementTree.parse(os.path.dirname(os.path.realpath(__file__)) + r'\gametimes.xml')
    game_times = {}
    games_xml = file.getroot()
    for game in games_xml.iter('game'):
        game_id = str(game.find('id').text)
        tt = game.find('time').text
        lasttimeplayed = game.find('lasttimeplayed').text
        game_times[game_id] = [tt, lasttimeplayed]
    return game_times


class BackendClient:

    def __init__(self):
        self.paths = []
        self.results = []
        self.roms = []
        self.BUF_SIZE = 65536

    def get_games_db(self):
        database_records = self.parse_dbf()

        self.get_rom_names()
        for rom in self.roms:
            best_record = []
            best_ratio = 0
            for record in database_records:
                if user_config.best_match_game_detection:
                    current_ratio = fuzz.token_sort_ratio(rom, record[1]) #Calculate the ratio of the name with the current record
                    if current_ratio > best_ratio:
                        best_ratio = current_ratio
                        best_record = record
                else:
                    #User wants exact match
                    if rom == record[1]:
                        self.results.append(
                            [record[0], record[1]]
                        )
            
            #Save the best record that matched the game
            if user_config.best_match_game_detection:
                self.results.append([best_record[0], best_record[1]])
        # database_records [sha1, name]
        # roms [name]
        '''
        for rom in self.roms:
            for record in database_records:
                db_hash = record[0]
                rom_hash = rom[0]
                if db_hash == rom_hash:
                    results.append(
                        [rom[0], record[1]]
                    )
        '''
        for x, y in zip(self.paths, self.results):
            x.extend(y)

        return self.paths

    def parse_dbf(self):
        records = []
        serials = []
        names = []
        with open(os.path.dirname(os.path.realpath(__file__)) + r'\gameList.txt', "r") as f:
            lines = f.readlines()
            for line in lines:
                split = line.split("=")
                if len(split) == 2:
                    game_id = split[0]
                    game_name = split[1]
                    if game_name not in names:
                        names.append(game_name)
                        serials.append(game_id)
        '''
        file = ElementTree.parse(os.path.dirname(os.path.realpath(__file__)) + r'\game.xml')
        games_xml = file.getroot()
        games = games_xml.findall('game')
        records = []
        serials = []
        names = []
        for game in games:
            game_id = game.find('id').text
            game_platform = game.find('type').text
            locale = game.find('locale')
            game_name = locale.find('title').text
            if game_platform == "GameCube":
                if game_name not in names:  # If the name isn't already in the list,
                    names.append(game_name)  # add it
                    serials.append(game_id)  # Add the serial
        
        records = []
        serials = []
        names = []
        root_element = file.getroot()
        for child in root_element:
            name = ""
            try:
                name = child.attrib["name"]
            except:
                name = ""
                #print("No Attribute 'name'")
                
            for category in child:
                sha1 = ""
                try:
                    sha1 = category.attrib["sha1"]
                except:
                    sha1 = ""
                    #print("No Attribute 'sha1'")

                if not name == "" and not sha1 == "":
                    if name not in names:
                        names.append(name)
                        serials.append(sha1)
                    #print("Name: " + records[sha1] + "\nSHA1: " + sha1)
        '''
        for serial, name in zip(serials, names):
            records.append([serial, name])

        return records

    def get_rom_names(self):
        # Search through directory for Dolphin ROMs
        cue_files = []
        '''
        for root, dirs, files in os.walk(user_config.roms_path):
            for file in files:
                if user_config.cue_search:
                    if file.lower().endswith((".cue")):
                        self.paths.append([os.path.join(root, file)])
                        self.roms.append(
                            os.path.splitext(os.path.basename(file))[0])  # Split name of file from it's path/extension
                else:
                    if file.lower().endswith((".bin", ".gz", ".iso", ".pbp", ".img")):
                        self.paths.append([os.path.join(root, file)])
                        self.roms.append(
                            os.path.splitext(os.path.basename(file))[0])  # Split name of file from it's path/extension
        '''
        for root, dirs, files in os.walk(user_config.roms_path):
            for file in files:
                if file.lower().endswith((".cue")):
                    cue_files.append(os.path.splitext(os.path.basename(file))[0])
                    self.paths.append([os.path.join(root, file)])
                    self.roms.append(
                            os.path.splitext(os.path.basename(file))[0])  # Split name of file from it's path/extension
                    
        for root, dirs, files in os.walk(user_config.roms_path):
            for file in files:
                if file.lower().endswith((".bin", ".gz", ".iso", ".pbp", ".img")):
                    filename = os.path.splitext(os.path.basename(file))[0]
                    if not filename in cue_files:
                        self.paths.append([os.path.join(root, file)])
                        self.roms.append(filename)
        '''
        for root, dirs, files in os.walk(user_config.roms_path):
            for file in files:
                if file.lower().endswith((".bin", ".gz", ".iso")):
                    sha1 = hashlib.sha1()
                    #with open(file, 'rb') as f:
                    filepath = os.path.join(root, file)
                    with open(filepath, 'rb') as f:
                        while True:
                            data = f.read(self.BUF_SIZE)
                            if not data:
                                break

                            sha1.update(data)
                                                        
                        sha1 = sha1.hexdigest()
                        path = os.path.join(root, file)
                        self.paths.append(path)
                        self.roms.append([sha1, os.path.splitext(os.path.basename(file))[0]])  # Split name of file from it's path/extension)
        '''

    def get_state_changes(self, old_list, new_list):
        old_dict = {x.game_id: x.local_game_state for x in old_list}
        new_dict = {x.game_id: x.local_game_state for x in new_list}
        result = []
        # removed games
        result.extend(LocalGame(id, LocalGameState.None_) for id in old_dict.keys() - new_dict.keys())
        # added games
        result.extend(local_game for local_game in new_list if local_game.game_id in new_dict.keys() - old_dict.keys())
        # state changed
        result.extend(
            LocalGame(id, new_dict[id]) for id in new_dict.keys() & old_dict.keys() if new_dict[id] != old_dict[id])
        return result
