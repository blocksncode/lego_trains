import curio
from bricknil import attach
from bricknil.sensor import TrainMotor, VisionSensor
from bricknil.const import Color
import os
import json
import logging
from bricknil import start
from bricknil.hub import PoweredUpHub
import subprocess
import datetime
from pydantic.schema import datetime

''' Lesson 2- This script connects to any active hubs and will then move them forward until the colour sensor senses yellow, 
then it will move backwards until it senses blue and then exit. '''

''' This gets the root (top level) folder path and then assigns a path for a sub folder where the hub info will be saved as a JSON file '''
ROOT = os.getcwd()
HUB_PATH = f'{ROOT}/hubs'
MAPPING_FILE = f'{HUB_PATH}/hub_mapping.json'

''' This sets the logging level (can be changed from INFO to DEBUG or CRITICAL etc. if preferred) '''
logging.basicConfig(level=logging.INFO)

''' This creates a new instance of a hub (train in this case) with the following attached to it:
1 x train motor
1 x colour/distance sensor (we only enable the colour sensor in this lesson)
'''
@attach(TrainMotor, name='motor')
@attach(VisionSensor, name='train_sensor', capabilities=['sense_color'])
class Train(PoweredUpHub):
    ''' The train class stores all variables related to the train and motors (such as speed) '''
    def __init__(self, name, ble_id):
        ''' This is where the parameters are passed to the Powered Up Hub class instance (these are mandatory, required by design) '''
        super().__init__(name=name, ble_id=ble_id)

        ''' This is where the parameters are stored in the Train class instance (although these are the same values as those passed to the Powered Up Hub class, 
        these are stored here to be used later for logging purposes) '''
        self.hub_name = name
        self.ble_id = ble_id
        self.colour = None
        self.keep_running = True

    ''' This runs once the Train is detected '''
    async def run(self):
        ''' Sets variables for controlling speed and direction '''
        top_forwards_speed = 20
        top_backwards_speed = -10
        reverse_colour = Color.yellow
        stop_colour = Color.blue
        logging.info(f"{self.hub_name} is running")

        ''' This sets the train speed to the number in the top_forwards_speed variable '''
        await self.motor.set_speed(top_forwards_speed)

        ''' This is a While loop that ensures the train keeps going until certain criteria are met '''
        while self.keep_running:
            ''' This shows the current colour detected by the sensor (just useful for testing) '''
            logging.info(self.colour)

            ''' This block determines what actions the train should take '''
            if self.colour == reverse_colour:
                ''' If the colour sensor detects the colour set in the reverse_colour variable then it stops and then reverses the direction of the train '''

                ''' First the motor speed is set to 0 to stop the train'''
                logging.info('Train stopping')
                await self.motor.set_speed(0)

                ''' Next we put in a sleep for 0 seconds 
                (this just ensures there is a fractional time gap between the previous and next commands so the motor has time to adjust)'''
                await curio.sleep(0)
                ''' Now the motor is set to the speed in the top_backwards_speed variable (negative denotes reverse)'''
                await self.motor.set_speed(top_backwards_speed)

            elif self.colour == stop_colour:
                ''' If the colour sensor detects the colour in the stop_colour variable then it sets the motor speed to 0 '''
                await self.motor.set_speed(0)

                ''' Next it sets the keep_running variable to False, which will then exit the While loop '''
                self.keep_running = False
            else:
                ''' We have a sleep for 0 seconds, which ensures there is a fractional time gap between actions 
                (otherwise the next action may occur to soon e.g. the motor direction and speed may change before the motor has stopped) '''
                await curio.sleep(0)

    ''' As we have attached a colour sensor we have to have a function to handle the sensor updates (mandatory) '''
    async def train_sensor_change(self):
        ''' This function updates the colour variable, based on the last value detected by the sensor
        (note by using Color() the colour is displayed in human readable format,
        we do not have to use this, but would then need to know that 7 = yellow etc.) '''
        self.colour = Color(self.train_sensor.value[VisionSensor.capability.sense_color])


''' This function prompts the user to name the hub '''
def prompt_for_hub_name(default_name):
    ''' This prompts the user to name the hub if it is a new entry, the user can just press enter to use the existing name '''
    hub_name = input(f"Enter a name for the new hub (default: {default_name}): ")
    return hub_name if hub_name.strip() else default_name

''' This is the main function that runs on startup '''
async def get_hubs():
    ''' Loads hubs from the mapping file, or exits if file is missing (the discover_hubs function should add any new hubs to the file) '''
    try:
        ''' Checks the pre-determined mapping file path, loads the file into memory and then assigns the data to the hubs_data variable as a Python dict by using json.load '''
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
        hub_info.update({'last_initiated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

    ''' This saves the updated (in memory) hub data to the mapping file '''
    with open(file_path, 'w') as f:
        ''' Using json.dump saves the list of Python dicts to the mapping file as a JSON '''
        json.dump(hubs_data, f, indent=4)

    ''' This reloads the mapping file and returns the new list '''
    with open(file_path, 'r') as f:
        return json.load(f)


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

''' We have to create a wrapper function due to the use of async (we will get an error if we don't use the await keyword as the function run_ble_scan may not have completed) '''
async def main():
    await run_ble_scan()

''' This checks the script is being run directly (i.e. not as a thread) and if so runs the main function then the get_hubs function '''
if __name__ == '__main__':
    ''' This runs the initial scan of available Bluetooth hubs '''
    curio.run(main())

    ''' This checks the mapping file (which contains details of the Bluetooth hubs) and initiates the hub '''
    start(get_hubs)
