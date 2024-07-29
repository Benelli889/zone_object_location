import os
import cv2
from thread_decorator import threaded
import numpy as np
import imutils
from typing import Optional, Union, Set, Tuple
from enum import Enum
from shutil import chown
import re
import json
from pyzm.interface import GlobalConfig, MLAPI_DEFAULT_CONFIG as DEFAULT_CONFIG


local_images_path = './images'
lp = 'ZONE_OBJ'

class ObjLocation():

    class location(Enum):
        init = -1
        outside_zone = 0
        inside_zone = 1
        partly_inside_zone = 2

    def __init__(self, g: GlobalConfig, EventID: int):
        """
        Initializes an instance of the ZoneObjectLocation class.
        """
        self.Event, self.Monitor, self.Frame = g.api.get_all_event_data(EventID)
        self.g = g

        self.zone_coordinates = []
        self.person_box = []
        self.location_zone = []
        self.image_list = []
        self.image_obj = None
        self.alarm_image = None
        self.EventFilePath = self.Event['FileSystemPath']
        self.MonitorID = self.Monitor['Id']
        self.width,self.height,self.c = 0,0,0


    def _draw_polygon(self, image, ptr: list) -> None:
        """
        Draws a polygon on the given image.
        """
        pts = np.array(ptr, np.int32)    
        cv2.polylines(image, [pts], True, (255, 0, 0), thickness=12)


    def _draw_rectangle_color(self, image, x, y, width, height, color=(255,0,0))-> None:
        """
        Draws a rectangle with the specified color on the given image.
        """
        cv2.rectangle(image, (x, y), (x + width, y + height), color, thickness=12)


    def _LoadObjectsJson(self, EventFolder: str) -> dict:
        """
        Load the objects.json file from the event folder.
        """
        try:
            os.path.exists(EventFolder + '/' + 'objects.json')  
        except Exception as all_ex:
            print(f"ERROR reading objects.json file: {EventFolder} -> {all_ex}")
            self.g.logger.error(
                f"{lp} ERROR reading objects.json file -> {all_ex}")
        else:
            f = open(EventFolder + '/' + 'objects.json')
            data = json.load(f)
            f.close()
        return data


    def get_zone_coordinates(self, MonID: int) -> list:
        """
        Retrieves the coordinates of all zones that meet the specified criteria.
        """
        # todo: make the search pattern configurable
        Zones_Monitor_name_tag = 'event'
        mon_zone_coords = []

        # Get all zones
        list_of_zones = self.g.api.zones()

        # todo: make the search configurable
        for zone in list_of_zones:
            if (     (zone.zone['Zone']['MonitorId'] == MonID)
                #and (zone.zone['Zone']['Type'] == 'Active')
                and (zone.zone['Zone']['Type'] == 'Inactive')
                and (re.findall(Zones_Monitor_name_tag, zone.zone['Zone']['Name']))):

                mon_zone_coords.append(zone.zone['Zone']['Coords'])
        self.zone_coordinates = mon_zone_coords

        return self.zone_coordinates


    def get_event_data(self) -> list:
        """
        Retrieves the event data from the JSON file and returns the width and height of the bounding box.
        """
        json_data = self._LoadObjectsJson(self.EventFilePath)

        self.labels = json_data['labels']
        self.bboxes = json_data['boxes']
        self.object_bboxes_list=[]

        for counter, value in enumerate(self.labels, start=0):

            # if value ==  person|dog|car...
            # todo: make the search pattern configurable
            if value in self.g.config['object_detection_pattern']:
                self.object_bboxes_list.append(self.bboxes[counter])

        if self.g.config['zone_object_detection_options'].get('zone_run_as_local_user', False):
            print(f"Object labels: [{', '.join(self.labels)}]")
        else:
            self.g.logger.debug(4, f"{lp} Object labels: [{', '.join(self.labels)}]")

        return self.object_bboxes_list


    def get_event_image_size(self) -> Tuple[int, int]:
        """
        Get the size of the camera event recording
        """
        try:
            self.image_obj = cv2.imread(self.EventFilePath + '/' + 'objdetect.jpg')
        except Exception as all_ex:
            if self.g.config['zone_object_detection_options'].get('zone_run_as_local_user', False):
                print(f"ERROR writing image event folders: , {self.EventFilePath} -> {all_ex}")
            else:            
                self.g.logger.error(
                    f"{lp} ERROR reading image event folders -> {all_ex}")
        else:
            self.height, self.width, self.c = self.image_obj.shape
            return self.width, self.height


    def draw_warning_dots_image(self, location_zone) -> None:
        """
        Draws warning points on the image based on the location zone.
        The color of the circle is determined by the zone state. If the 
        zone state is 'inside_zone', the circle is drawn in red color,
        otherwise it is drawn in green color.

        The resulting image with the warning dots is saved to a file in 
        the event folder.
        """
        # Center coordinates
        radius = 50
        # Line thickness of -1 px 
        thickness = -1

        for number, zone_state in enumerate(location_zone):

            if zone_state == self.location.inside_zone:
                # Red color in BGR
                color = (0, 0, 255) 
            elif zone_state == self.location.partly_inside_zone:
                # Red color in BGR
                color = (255, 125, 255) 
            else:
                # Green color in BGR
                color = (125, 255, 125) 
            
            # Coordinates x from left to right
            center_x = self.width - (number+1) * (radius*2) - ((number+1)*10)
            center_coordinates = (center_x, radius+10)

            if center_x > 0 + radius:
                # Draw a circle
                self.alarm_image = cv2.circle(self.image_obj, center_coordinates, radius, color, thickness) 

        if self.g.config['zone_object_detection_options'].get('zone_run_as_local_user', False):
            path_and_filename = f'{local_images_path}/obj_alarm.jpg'
        else:
            path_and_filename = f'{self.EventFilePath}/obj_alarm.jpg'

        try:
            result = cv2.imwrite(path_and_filename, self.alarm_image)
        except Exception as all_ex:
            print(f"ERROR writing image event folders: , {path_and_filename} -> {all_ex}")
            self.g.logger.error(
                f"{lp} ERROR writing image event folders -> {all_ex}")
        else:
            try:
                chown(path_and_filename, 'www-data', 'www-data')
            except Exception as all_ex:
                print(f"ERROR writing image event folders: , {path_and_filename} -> {all_ex}")
                self.g.logger.error(
                    f"{lp} ERROR writing image event folders -> {all_ex}")
        return result


    def store_images_of_zones(self) -> None:
        """
        Each image is saved to event-folder with a unique filename based on 
        object number.
        """
        for counter, image in enumerate(self.image_list):
            path_and_filename = f'{self.EventFilePath}/zone_{counter}.jpg'
            if self.g.config['zone_object_detection_options'].get('zone_run_as_local_user', False) == True:
                result = cv2.imwrite(f'{local_images_path}/zone_{counter}.jpg', image)
            else:
                try:
                    result = cv2.imwrite(f'{self.EventFilePath}/zone_{counter}.jpg', image)
                except Exception as all_ex:
                    print(f"ERROR writing image event folders: {path_and_filename} -> {all_ex}")
                    self.g.logger.error(
                        f"{lp} ERROR writing image event folders -> {all_ex}")
                else:
                    try:
                        chown(path_and_filename, 'www-data', 'www-data')
                    except Exception as all_ex:
                        print(f"ERROR writing image event folders: {path_and_filename} -> {all_ex}")
                        self.g.logger.error(
                            f"{lp} ERROR writing image event folders -> {all_ex}")
        return result


    def calc_location(self) -> location:
        """
        Calculates the location of object bounding boxes within zones.
        """
        gray_level = 127

        for zones in self.zone_coordinates:
            zones_pts = zones.split(' ')
            zones_pts = [list(map(int, x.split(','))) for x in zones_pts]


        self.location_zone.clear()
        for object_bbox_counter, object_bbox, in enumerate(self.object_bboxes_list):

            blank_image = gray_level * np.ones(shape=(self.height, self.width, self.c), dtype=np.uint8)

            #pts = np.array(zones_pts, np.int32)    
            self._draw_polygon(blank_image, zones_pts)

            # get lenght of the object bounding box

            # convert image to a grayscale
            gray_scaled = cv2.cvtColor(blank_image, cv2.COLOR_BGR2GRAY)

            # thresholding the image
            thresh = cv2.threshold(gray_scaled, 125, 125, cv2.THRESH_BINARY_INV)[1]

            # find contours in thresholded image
            contours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours = imutils.grab_contours(contours)

            length_zone = cv2.contourArea(contours[0]) 


            self._draw_rectangle_color(blank_image, 
                                object_bbox[0], 
                                object_bbox[1], 
                                object_bbox[2]-object_bbox[0], 
                                object_bbox[3]-object_bbox[1], 
                                (0, 120, 0))

            # convert image to a grayscale
            gray_scaled = cv2.cvtColor(blank_image, cv2.COLOR_BGR2GRAY)

            # thresholding the image
            thresh = cv2.threshold(gray_scaled, 125, 125, cv2.THRESH_BINARY_INV)[1]

            # find contours in thresholded image
            contours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours = imutils.grab_contours(contours)

            length_object = cv2.contourArea(contours[0]) 

            image_contours = blank_image.copy()
            for contour in contours:
                cv2.drawContours(image_contours, [contour], -1, (240, 0, 159), 10) 

            # draw original image and the overlay weighted
            self.image_weighted = cv2.addWeighted(self.image_obj, .6, image_contours, .9, 0)

            self.image_list.append(self.image_weighted)

            if len(contours) > len(self.zone_coordinates):
                self.location_zone.append(self.location.outside_zone)
            else:
                # if the zone has increased in size
                if length_object > length_zone:
                    self.location_zone.append(self.location.partly_inside_zone)
                else:
                    self.location_zone.append(self.location.inside_zone)

        return self.location_zone


    def ObjLocationFilterDetections(self) -> location:
        """
        calculates the location of objects filters detections
        """
        
        # Queries the zone coordinates from the zm-api
        if self.get_zone_coordinates(self.MonitorID) != []:
            print(f"Zone coordinates: {self.zone_coordinates}")

        if self.get_event_image_size() != []:
            print(f"Image size: {self.width} x {self.height}")

        # Retrieves the event data
        if self.get_event_data() != []:
            print(f"Object bounding boxes: {self.object_bboxes_list}")  

        # Calculates the location of objects
        location_list = self.calc_location()
        if location_list != []:
            print(f"Location list: {location_list}")
            
        return location_list


    # @threaded()
    def ObjLocationAll(self) -> None:
        """
        Performs the complete object location process
        """

        # Queries the zone coordinates from the zm-api
        if self.get_zone_coordinates(self.MonitorID) != []:
            print(f"Zone coordinates: {self.zone_coordinates}")

        if self.get_event_image_size() != []:
            print(f"Image size: {self.width} x {self.height}")

        # Retrieves the event data
        if self.get_event_data() != []:
            print(f"Object bounding boxes: {self.object_bboxes_list}")  

        # Calculates the location of objects
        location_list = self.calc_location()
        if location_list != []:
            print(f"Location list: {location_list}")

        # Draws warning dots on the image based on the calculated location
        if self.draw_warning_dots_image(location_list) != True:
            print("Error drawing warning dots on image")

        # Stores the image on the local file system / event folder 
        if self.store_images_of_zones() != True:
            print("Error storing images of zones") 
        else:
            print("Images stored successfully")

        return location_list