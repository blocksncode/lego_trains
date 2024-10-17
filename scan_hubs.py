import logging
import asyncio
import json
from bleak import BleakScanner
import os

''' This gets the root (top level) folder path (where this script is saved) '''
ROOT = os.getcwd()

''' This sets the path where the hub info will be saved as a JSON file '''
MAPPING_FILE = f'{ROOT}/hubs/hub_mapping.json'

''' This sets the logging level (can be changed from INFO to DEBUG or CRITICAL etc. if preferred), 
so we can see what our script is trying to do (can be useful if something goes wrong) '''
logging.basicConfig(level=logging.INFO)

''' This is the main function used to discover the available Hubs '''
async def discover_hubs():
    ''' This function scans for available Bluetooth devices and adds any newly discovered active hubs to the mapping file '''
    logging.info("Scanning for Smart Hubs...")

    ''' Scans for available hubs and then adds to the devices variable '''
    devices = await BleakScanner.discover(timeout=1)

    ''' Loads existing hubs from the mapping file to the hubs variable as a Python list '''
    hubs = load_existing_hubs()

    ''' Count and then display the number of existing hubs '''
    hub_count = len(hubs)
    logging.info(f'{hub_count} hubs currently in mapping file.')

    ''' Loops through the active Bluetooth devices'''
    for dev in devices:
        ''' Checks if Smart Hub is in the device name (that is the name used for Lego PoweredUp Hubs) '''
        if dev.name and 'Smart Hub' in dev.name:
            ''' Gets the device id '''
            ble_id = dev.address

            ''' Checks to see if the device id is in the hubs list (which was loaded from the mapping file) '''
            if ble_id not in [h['ble_id'] for h in hubs]:
                ''' If the device id is not in the hubs list/mapping list, assigns a default name of train_n, where n is the hub count + 1 '''
                default_name = f"train_{hub_count + 1}"

                ''' Appends the new hub to the hubs list and sets the new flat to True so the user will get prompted to name the hub later '''
                hubs.append({'hub_name': default_name, 'ble_id': ble_id, 'new': True})

    ''' Saves the hub list to the mapping file '''
    save_hubs_to_json(hubs)

''' This loads existing hubs from the mapping file '''
def load_existing_hubs(file_path=MAPPING_FILE):
    ''' Checks if the mapping file exists and returns the mappings, otherwise returns an empty list '''
    if os.path.exists(file_path):
        try:
            ''' If the mapping file does exist then loads the data into memory '''
            with open(file_path, 'r') as f:
                ''' Returns the data as a list of Python dicts by using json.load '''
                return json.load(f)
        except json.JSONDecodeError:
            ''' If the file is empty or contains invalid JSON, return an empty list '''
            logging.info(f"{file_path} contains invalid JSON or is empty. A new mapping file will be created.")
            return []
    else:
        ''' If the file doesn't exist, return an empty list '''
        return []

''' This saves hubs to the mapping file '''
def save_hubs_to_json(hubs, file_path=MAPPING_FILE):
    ''' Creates a new mapping file and then overwrites (or creates if one does not exist) '''
    with open(file_path, 'w') as f:
        ''' Using json.dump saves the list of Python dicts to the mapping file as a JSON '''
        json.dump(hubs, f, indent=4)

if __name__ == '__main__':
    asyncio.run(discover_hubs())

