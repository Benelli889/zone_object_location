import os
import json

def getEventFolder(EventsFolder, Event) -> str | None:

    EventFolder = None

    for root, dirs, files in os.walk(EventsFolder):
        for dir in dirs:
            if dir == str(Event):
                EventFolder = root + '/' + dir

    return EventFolder


def LoadObjectsJson(EventFolder : str) -> dict:

    # Opening JSON file
    f = open(EventFolder + '/' + 'objects.json')
    
    # returns JSON object as a dictionary
    data = json.load(f)
    f.close()

    return data


def LoadZones(EventFolder : str) -> dict:

    # Opening JSON file
    file = EventFolder + '/' + 'zones.html'
    #f = open(EventFolder + '/' + 'zones.html')

    with open(file, 'r') as file:
        data = file.read().rstrip()    

    # returns JSON object as a dictionary
    #data = f.read()
    file.close()

    return data

