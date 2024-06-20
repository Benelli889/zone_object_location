# main program
import os
import sys 
import time
from pyzm.interface import ZMESConfig
from pyzm.interface import GlobalConfig, MLAPI_DEFAULT_CONFIG as DEFAULT_CONFIG
from pyzm.helpers.pyzm_utils import LogBuffer
from pyzm.api import ZMApi
import yaml
import zone_obj_locaction as zol

yaml_file_path = './yaml/'
CONFIG_PATH = rf'{yaml_file_path}objectconfig.yml'
SECRETS_LOCAL = rf'{yaml_file_path}secrets.yml'

# CONFIG_PATH = rf'{os.path.expanduser("~")}{yaml_file_path}objectconfig.yml'
# SECRETS_LOCAL = rf'{os.path.expanduser("~")}{yaml_file_path}secrets.yml'
#g: GlobalConfig


# Load local secrets from yaml file
def _LoadSecretsYAML(secrets_file: str) -> dict:
    """
    Load secrets from a YAML file.
    """
    with open(secrets_file, 'r') as file:
        secrets_yml = yaml.safe_load(file)
    return secrets_yml


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
    return version['status'], version['zm_version']


def main():

    status, version = ConnectZMApi()
    print(f"ZM-Version: {version} - Status: {status}")

    ###############
    EventID = 25327
    ###############

    _, Monitor, _ = g.api.get_all_event_data(EventID)

    obj_loc = zol.ObjLocaction(g, EventID)
    # obj_loc.getZoneCoordinates(Monitor['Id'])
    # obj_loc.get_Event()
    # obj_loc.calc_location()
    # location_list = obj_loc.calc_location()
    # obj_loc.draw_warning_dots_image(location_list)

    obj_loc.ObjLocactionAll()



if __name__ == "__main__":

    start_of_objdet_py = time.perf_counter()
    try:
        main()

    except Exception as all_ex:
        print(f"ERROR:  {all_ex}")
        # g.logger.error(
        #     f"{main} ERROR -> {all_ex}")

    print(f'Total time objdet: {time.perf_counter() - start_of_objdet_py} sec')


