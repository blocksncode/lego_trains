''' Lesson 1- This script connects to any active hubs and will then move them forward and backwards briefly '''

''' These are the libraries we need to import to use in our script '''
import curio
from bricknil import attach
from bricknil.sensor import TrainMotor
import os
import json
import logging
from bricknil import start
from bricknil.hub import PoweredUpHub
import subprocess
import datetime

''' This gets the root (top level) folder path (where this script is saved) '''
ROOT = os.getcwd()

''' This sets the path where the hub info will be saved as a JSON file '''
MAPPING_FILE = f'{ROOT}/hubs/hub_mapping.json'

''' This sets the logging level (can be changed from INFO to DEBUG or CRITICAL etc. if preferred), 
so we can see what our script is trying to do (can be useful if something goes wrong) '''
logging.basicConfig(level=logging.INFO)

''' This creates a new instance of a hub (train in this case) with a single motor attached to it '''
@attach(TrainMotor, name='motor')
class Train(PoweredUpHub):
    ''' The train class stores all variables related to the train and motors (such as speed) '''
    def __init__(self, name, ble_id):
        ''' This is where the parameters are passed to the Powered Up Hub class instance (these are mandatory, required by design) '''
        super().__init__(name=name, ble_id=ble_id)

        ''' This is where the parameters are stored in the Train class instance (although these are the same values as those passed to the Powered Up Hub class, 
        these are stored here to be used later for logging purposes) '''
        self.hub_name = name
        self.ble_id = ble_id

    ''' This runs once the Train is detected '''
    async def run(self):
        ''' This function lets the train accelerate to a pre-set speed, before stopping and reversing back '''

        ''' Sets variables for controlling speed and direction '''
        seconds_for_acceleration = 2
        seconds_for_deceleration = 0.5
        top_forwards_speed = 40
        top_backwards_speed = -40
        logging.info(f"{self.hub_name} is running")

        ''' This accelerates the train to the pre-set top speed over the pre-set number of seconds (denoted in milliseconds, hence we multiply by 1000) '''
        await self.motor.ramp_speed(top_forwards_speed, seconds_for_acceleration * 1000)

        ''' This ensures no other commands are sent until the specified time period for acceleration has passed '''
        await curio.sleep(seconds_for_acceleration)

        ''' This decelerates the train to the pre-set top speed over the pre-set number of seconds (denoted in milliseconds, hence we multiply by 1000) '''
        await self.motor.ramp_speed(0, seconds_for_deceleration * 1000)

        ''' This ensures no other commands are sent until the specified time period for deceleration has passed '''
        await curio.sleep(seconds_for_deceleration)

        ''' This accelerates the train to the pre-set top (reverse) speed over the pre-set number of seconds (denoted in milliseconds, hence we multiply by 1000) '''
        await self.motor.ramp_speed(top_backwards_speed, seconds_for_acceleration * 1000)

        ''' This ensures no other commands are sent until the specified time period for acceleration has passed '''
        await curio.sleep(seconds_for_acceleration)

        ''' This decelerates the train to the pre-set top speed over the pre-set number of seconds (denoted in milliseconds, hence we multiply by 1000) '''
        await self.motor.ramp_speed(0, seconds_for_deceleration * 1000)

''' This function prompts the user to name the hub '''
def prompt_for_hub_name(default_name):
    ''' This prompts the user to name the hub if it is a new entry, the user can just press enter to use the existing name '''
    hub_name = input(f"Enter a name for the new hub (default: {default_name}): ")
    return hub_name if hub_name.strip() else default_name

''' This updates the mapping file '''
def update_mapping_file(hubs_data, file_path=MAPPING_FILE):
    ''' This updates the mapping file based on the new name of the hub (can be unchanged) and the current time to show when it was last initiated '''

    ''' Loops through all the hubs in the mapping file'''
    for hub_info in hubs_data:
        ''' If the new key is in the current hub entry and is set to True, prompts the user to update the hub name '''
        if 'new' in hub_info.keys() and hub_info['new'] is True:
            ''' This will update the hub information (in memory) with the new name and also sets the new key to False, 
            so on the next initiation the user is not prompted to change the name again'''
            hub_info.update({'hub_name': prompt_for_hub_name(hub_info['hub_name']), 'new': False})

        ''' This updates the hub info (in memory) with the current date and time to show when the last initiation took place '''
        hub_info.update({'last_initiated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

    ''' This saves the updated (in memory) hub data to the mapping file '''
    with open(file_path, 'w') as f:
        ''' Using json.dump saves the list of Python dicts to the mapping file as a JSON '''
        json.dump(hubs_data, f, indent=4)

    ''' This reloads the mapping file and returns the new list '''
    with open(file_path, 'r') as f:
        return json.load(f)

''' This is the main function that runs on startup '''
async def get_hubs():
    ''' Loads hubs from the mapping file, or exits if file is missing (the discover_hubs function should add any new hubs to the file) '''
    try:
        ''' Checks the pre-determined mapping file path, loads the file into memory and then 
        assigns the data to the hubs_data variable as a Python dict by using json.load '''
        with open(MAPPING_FILE, 'r') as f:
            hubs_data = json.load(f)
    except FileNotFoundError:
        ''' If the mapping file does not exist it exits the script as it can not proceed with at least 1 active hub '''
        logging.error('Mapping file not found. Please run discover_hubs function first.')

    if not hubs_data:
        ''' If the mapping file exists, but is empty then the script also terminates as it can not proceed without at least 1 active hub '''
        logging.error('No hubs found in the mapping file.')

    ''' Checks to see if there are any new entries to the mapping list and prompts the user to re-name them '''
    updated_hubs_data = update_mapping_file(hubs_data, file_path=MAPPING_FILE)

    ''' Loops through each hub one and creates a new instance of the Train class '''
    for hub_info in updated_hubs_data:
        ''' Creates new instance of Train class for each hub detected '''
        logging.info(f"Initiating hub name: {hub_info['hub_name']}, ble id: {hub_info['ble_id']}")
        Train(hub_info['hub_name'], ble_id=hub_info['ble_id'])

''' This function runs our scan_hubs script as a sub process to detect any active hubs.
We have to run it from a different script as a sub process as it uses a different library to bricknil 
and this causes conflicts when run in the main script. '''
async def run_ble_scan():
    ''' This function runs the scan_hubs script (which is used to scan for active Bluetooth hubs) as a sub process '''
    logging.info("Running BLE scan subprocess...")

    ''' Run the external script using subprocess '''
    process = subprocess.Popen(['python3', 'scan_hubs.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    ''' Once the scan has completed, displays the output to the user '''
    stdout, stderr = process.communicate()

    ''' Check if the subprocess completed successfully '''
    if process.returncode != 0:
        logging.info(f"Error in Hub detection subprocess: {stderr.decode()}, exiting script.")
    else:
        logging.info(f"Subprocess completed successfully: {stdout.decode()}")

''' We have to create a wrapper function due to the use of async (we will get an error if we don't use the await 
keyword as the function run_ble_scan may not have completed) '''
async def main():
    await run_ble_scan()

''' This checks the script is being run directly (i.e. not as a thread) and if so runs the main function then the get_hubs function '''
if __name__ == '__main__':
    ''' This runs the initial scan of available Bluetooth hubs '''
    curio.run(main())

    ''' This checks the mapping file (which contains details of the Bluetooth hubs) and initiates the hub '''
    start(get_hubs)
