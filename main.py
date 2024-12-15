import os
import sys 
import time
from pyzm.interface import ZMESConfig
from pyzm.interface import GlobalConfig, MLAPI_DEFAULT_CONFIG as DEFAULT_CONFIG
from pyzm.helpers.pyzm_utils import LogBuffer
from pyzm.api import ZMApi
import yaml
import zone_obj_loc as zol

yaml_file_path = './yaml'
CONFIG_PATH = rf'{yaml_file_path}/objectconfig.yml'
SECRETS_LOCAL = rf'{yaml_file_path}/secrets.yml'
lp = 'ZONE_OBJ'


# Load local secrets from yaml file
def _LoadSecretsYAML(secrets_file: str) -> dict:
    """
    Load secrets from a YAML file.
    """
    with open(secrets_file, 'r') as file:
        secrets_yml = yaml.safe_load(file)
    return secrets_yml


def WriteDebugMsgToLogFile() -> None:
    """
    Writes debug messages to a log file.
    This function reads the debug messages from the logger buffer, sorts them by timestamp,
    and writes them to a log file in the format:
    """
    # g.logger.log_close()
    Log_file_name_and_path = os.getcwd() + '/' + 'objdet.log'

    outfile = open(Log_file_name_and_path, 'wt')

    if g.logger.buffer and len(g.logger.buffer):
        # sort it by timestamp
        g.logger.buffer = sorted(
            g.logger.buffer, key=lambda x: x["timestamp"], reverse=True)
        for _ in range(len(g.logger.buffer)):
            line = g.logger.buffer.pop() if len(g.logger.buffer) > 0 else None
            if line:
                fnfl = f"{line['filename']}:{line['lineno']}"
                print_log_string = (
                    f"{line['timestamp']} LOG_BUFFER[{os.getpid()}] {line['display_level']} "
                    f"{fnfl} [{line['message']}]"
                )
                print(print_log_string, file=outfile)
    outfile.close()


def ConnectZMApi():
    """
    Connects to the ZM-API using the provided credentials
    """
    global g
    g = GlobalConfig()
    g.logger = LogBuffer()

    mlc: ZMESConfig = ZMESConfig(CONFIG_PATH, DEFAULT_CONFIG, "mlapi") 
    g.config = mlc.config

    # Set credentials
    secret = _LoadSecretsYAML(SECRETS_LOCAL)
    api_options = {
        "apiurl": secret['secret']['ZM_API_PORTAL'],
        "portalurl": secret['secret']['ZM_PORTAL'],
        'user': secret['secret']['ZM_USER'],
        'password': secret['secret']['ZM_PASSWORD'],
        'basic_auth_user': secret['secret']['ZM_BASIC_USER'],
        'basic_auth_password': secret['secret']['ZM_BASIC_PASS']
    }

    # Connect to ZM-API
    g.api = ZMApi(options=api_options)

    # Check if connection is established
    version = g.api.version()
    #g.config['log_level_debug'] = 3
    return version['status'], version['zm_version']


def main():
    status, version = ConnectZMApi()

    zone_run_as_local_user = g.config['zone_object_detection_options'].get('zone_run_as_local_user', False)

    if zone_run_as_local_user == True:
        print(f"ZM-Version: {version} - Status: {status} - Running as local user")
    else:
        g.logger.info(f"{lp} ZM-Version: {version} - Status: {status}")

    ###############
    # Chossing the event to be processed
    EventID = 31271
    ###############

    _, Monitor, _ = g.api.get_all_event_data(EventID)

    obj_loc = zol.ObjLocation(g, EventID)

    run_functions_individually = False

    #################################################

    if run_functions_individually == True:

        # Queries the zone coordinates from the zm-api
        zone_coordinates = obj_loc.get_zone_coordinates(Monitor['Id'])
        if zone_coordinates != []:
            if zone_run_as_local_user == True:
                print(f"Zone coordinates: {zone_coordinates}")
            else:
                g.logger.debug(4, f"{lp} Zone coordinates: {zone_coordinates}")
        else:
            if zone_run_as_local_user == True:
                print(f"Failure: Zone coordinates: {zone_coordinates}")
            else:
                g.logger.error(f"{lp} Can't retrive Zone-coordinates: {zone_coordinates}")

        # Queries the event image size from the zm-api
        width, hight = obj_loc.get_event_image_size()
        if width != 0 or hight != 0:
            if zone_run_as_local_user == True:
                print(f"Image size: {width} x {hight}") 
            else:
                g.logger.debug(4, f"{lp} Image size: {width} x {hight}")
        else:   
            if zone_run_as_local_user == True:
                print(f"No image size: {width} x {hight}") 
            else:
                g.logger.error(f"{lp} Image cannot be read: size: {width} x {hight}")

        # Retrieves the event data
        object_bboxes_list = obj_loc.get_event_data()
        if object_bboxes_list != []:
            if zone_run_as_local_user == True:
                print(f"Object bounding boxes: {object_bboxes_list}")  
            else:
                g.logger.debug(4, f"{lp} Object bounding boxes: {object_bboxes_list}")
        else:
            if zone_run_as_local_user == True:
                print(f"Cannot read object bounding boxes: {object_bboxes_list}")  
            else:
                g.logger.error(f"{lp} Cannot read object bounding boxes: {object_bboxes_list}")

        # Calculates the location of objects
        location_list = obj_loc.calc_location()
        if location_list != []:
            if zone_run_as_local_user == True:
                print(f"Location list: {location_list}")
            else:
                g.logger.debug(4, f"{lp} Location list: {location_list}")
        else:
            if zone_run_as_local_user == True:
                print(f"No location list: {location_list}")
            else:
                g.logger.error(f"{lp} No location list: {location_list}")

        # Checks if the object pattern is inside the zone
        location_zone_set = {loc.value for loc in location_list}
        
        if (obj_loc.location.inside_zone.value in location_zone_set)                       or     \
            ((obj_loc.location.partially_inside_zone.value in location_zone_set)              and    \
            (g.config['zone_object_detection_options'].get('consider_partially_inside_zone', False))):

            g.logger.debug(
                f"{lp} Object pattern is inside zone {location_list}"
            )
        else:
            g.logger.debug(
                f"{lp} No object pattern inside zone {location_list}"
            )

        # Draws warning dots on the image based on the calculated location
        restult_warning_image =  obj_loc.draw_warning_dots_image(location_list)
        if restult_warning_image == True:
            if zone_run_as_local_user == True:
                print("Warning dots drawn not successful")
            else:
                g.logger.debug(4, f"{lp} Warning dots drawn not successful")
        else:
            if zone_run_as_local_user == True:
                print("Warning dots drawn successfully")
            else:
                g.logger.error(f"{lp} Warning dots drawn not successfully")

        # Stores the image on the local file system / event folder 
        restult_zone_image =  obj_loc.store_images_of_zones()
        if restult_zone_image == True:
            if zone_run_as_local_user == True:
                print("Images stored successfully")
            else:
                g.logger.debug(4, f"{lp} Images stored successfully")
        else:
            if zone_run_as_local_user == True:
                    print("Images NOT stored successfully")
            else:
                    g.logger.error(f"{lp} Images NOT stored successfully")

    else:

        # Object zone detection
        #################################################

        ret_location_list = obj_loc.ObjLocationAll()

        g.logger.debug(f"{lp} ret_location_list {ret_location_list}")

        for location_list in ret_location_list:

            if location_list == obj_loc.location.inside_zone:
                # do specific alaming for inside_zone
                pass
            
            if location_list == obj_loc.location.partially_inside_zone:
                # do specific alaming for each partially_inside_zone
                pass

            if location_list == obj_loc.location.outside_zone:
                # do specific alaming for outside_zone
                pass



if __name__ == "__main__":

    start_of_objdet_py = time.perf_counter()

    try:
        main()

    except Exception as all_ex:
        print(f"ERROR:  {all_ex}")
        g.logger.error(
            f"{main} ERROR -> {all_ex}")
    main()

    print(f'Total time {lp}: {time.perf_counter() - start_of_objdet_py} sec')
    g.logger.info(f"{lp} Total time {lp}: {time.perf_counter() - start_of_objdet_py} sec")

    WriteDebugMsgToLogFile()
    g.logger.log_close()

