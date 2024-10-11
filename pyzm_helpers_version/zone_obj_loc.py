#!/usr/bin/python3
import os
import cv2
from more_itertools import one
import numpy as np
import imutils
from typing import Optional, Union, Set, Tuple
from enum import Enum
from shutil import chown
import re
import json
from pyzm.interface import GlobalConfig, MLAPI_DEFAULT_CONFIG as DEFAULT_CONFIG
import pyzm.helpers.pyzm_utils
from pyzm.helpers.pyzm_utils import get_www_user

lp: str = 'zone_obj'
webuser, webgroup = get_www_user()

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
        IMG_DEPTH=3
        self.Event, self.Monitor, self.Frame = g.api.get_all_event_data(EventID)
        self.g = g

        self.zone_coordinates = []
        self.person_box = []
        self.location_zone = []
        self.location_list = []
        self.image_list = []
        self.image_obj = None
        self.alarm_image = None
        self.EventFilePath = self.Event['FileSystemPath']
        self.MonitorID = self.Monitor['Id']
        #self.width,self.height,self.c = 0,0,0
        self.width, self.height, self.c = self.Event["Width"], self.Event["Height"], IMG_DEPTH
        self.current_frameID = 0


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
                and (zone.zone['Zone']['Type'] == 'Active')
                and (re.findall(Zones_Monitor_name_tag, zone.zone['Zone']['Name']))):

                mon_zone_coords.append(zone.zone['Zone']['Coords'])
        self.zone_coordinates = mon_zone_coords

        if self.zone_coordinates == []:
            self.g.logger.info(f"{lp} Can't retrive event-Zone-coordinates: {self.zone_coordinates}")

        else:
            for zones in self.zone_coordinates:
                zones_pts = zones.split(' ')
                zones_pts = [list(map(int, x.split(','))) for x in zones_pts]

            self.zone_coordinates = zones_pts

        return self.zone_coordinates


    def get_zone_coordinates_Inkscape_html(self, MonID: int) -> list:
        """
        Retrieves the coordinates of zone from the html - Inkscape file -> object_zone.html.
        """

        # todo: make the algorithm more robust

        def LoadZones(EventFolder : str) -> str:
            # open zones.html
            file = EventFolder

            # returns zone data as string
            with open(file, 'r') as file:
                data = file.read().rstrip()    
            file.close()
            return data

        # Get Monitor file path
        # eg: '/mnt/DiskVerbatimVi55/ZMEvents/8/2024-08-15/31259'
        object_zone_html = self.g.config['zone_object_detection_options'].get('Inkscape_zones_file_name', '')

        pattern = str(self.MonitorID) + '/'
        pos = re.search(pattern, self.EventFilePath).start()
        object_zone_filename = self.EventFilePath[0:pos + len(pattern)] + object_zone_html

        #zone_data = LoadZones("/mnt/DiskVerbatimVi55/ZMEvents/8/object_zone.html")

        try:
            zone_data = LoadZones(object_zone_filename)
        except Exception as all_ex:
            self.g.logger.info(f"{lp} Can't read Inkscape zones file: {self.EventFilePath}")
            self.zone_coordinates = []
        else:

            start_of_polygon_coord = zone_data.split('moveTo')
            polygon_coord_raw = re.findall(r"[-+]?\d*\.\d+|\d+", start_of_polygon_coord[1])

            # Convert list of strings to list of integers
            polygon_coord = [int(float(x)) for x in polygon_coord_raw]   

            # Convert list of tuple
            polygon_coord_tupel = ([(polygon_coord[i], polygon_coord[i+1]) for i in range(0, len(polygon_coord), 2)])

            # Convert list of lists
            polygon_coord_list = [list(i) for i in polygon_coord_tupel]
            self.g.logger.info(f"{lp} Inkscape zones: {polygon_coord_list}")
            zone_coordinates_Inkscape = polygon_coord_list

            self.zone_coordinates = zone_coordinates_Inkscape

        return self.zone_coordinates


    def get_event_sequence_detect_data(self) -> list:
        """
        Retrieves the event data from the JSON file and returns the width and height of the bounding box.
        """
        # self.bboxes
        # self.labels
       
        self.object_bboxes_list=[]
        zone_object_pattern = re.findall(r"[a-z]+", self.g.config['zone_object_detection_options'].       \
                                                            get('zone_object_detection_pattern', ''))

        for counter, value in enumerate(self.labels, start=0):

            # if value ==  person|dog|car...
            if value in zone_object_pattern:
                self.object_bboxes_list.append(self.bboxes[counter])

        self.g.logger.debug(4, f"{lp} Object labels: [{', '.join(self.labels)}]")
        return self.object_bboxes_list


    def warning_dots_draw(self, location_zone) -> None:
        """
        Draws warning points on the image based on the location zone.
        The color of the circle is determined by the zone state. 
        - zone state is 'inside_zone' red color,
        - zone state is 'partly_inside_zone' pink color,
        - otherwise it is drawn in green color.

        The resulting image with the warning dots is saved to a file in 
        the event folder.
        """
        # Center coordinates
        radius = 50
        # Line thickness of -1 px 
        thickness = -1

        for number, zone_state in enumerate(location_zone):

            if zone_state == self.location.inside_zone                          or     \
                (zone_state == self.location.partly_inside_zone                and     \
                self.g.config['zone_object_detection_options'].get('consider_partially_inside_zone') == True):
                # Red color in BGR
                color = (0, 0, 255) 
            elif zone_state == self.location.partly_inside_zone:
                # pink color in BGR
                color = (125, 125, 255) 
            else:
                # Green color in BGR
                color = (125, 255, 125) 
            
            # Coordinates x from left to right
            center_x = self.width - (number+1) * (radius*2) - ((number+1)*10)
            center_coordinates = (center_x, radius+10)

            if center_x > 0 + radius:
                # Draw a circle
                try:
                    # draw original image and the overlay weighted
                    self.alarm_image = cv2.circle(self.image_obj, center_coordinates, radius, color, thickness) 
                except Exception as all_ex:
                    self.g.logger.error(
                        f"{lp} ERROR drawing image -> {all_ex}")

        path_and_filename = f'{self.EventFilePath}/obj_alarm.jpg'

        try:
            result = cv2.imwrite(path_and_filename, self.alarm_image)
        except Exception as all_ex:
            self.g.logger.error(
                f"{lp} ERROR writing image event folders -> {all_ex}")
        else:
            try:
                chown(path_and_filename, webuser, webgroup)
            except Exception as all_ex:
                self.g.logger.error(
                    f"{lp} ERROR writing image event folders -> {all_ex}")
        return result


    def zones_images_save(self) -> None:
        """
        Each image is saved to event-folder with a unique filename based on 
        object number.
        """
        # self.image_list.append( dict ( image = self.image_weighted, loc =  location_zone))
        radius = 50

        for number, image_dic in enumerate(self.image_list):

            image = image_dic['image']

            if image_dic["loc"] == self.location.inside_zone                   or     \
                (image_dic["loc"] == self.location.partly_inside_zone          and    \
                self.g.config['zone_object_detection_options'].get('consider_partially_inside_zone') == True):

                # Red color in BGR
                color = (0, 0, 255) 
            elif image_dic["loc"] == self.location.partly_inside_zone:
                # pink color in BGR
                color = (100, 0, 125) 
            else:
                # Green color in BGR
                color = (125, 255, 125) 
            
            # Coordinates x from left to right
            center_x = self.width - (radius*2) - 20
            center_coordinates = (center_x, radius+10)

            if center_x > 0 + radius:
                # Draw a circle
                try:
                    # draw original image and the overlay weighted
                    alarm_image = cv2.circle(image, center_coordinates, radius, color, thickness=-1) 
                except Exception as all_ex:
                    self.g.logger.error(
                        f"{lp} ERROR drawing image -> {all_ex}")

            # wite warning dots on any other image
            objdetect = cv2.imread(self.EventFilePath + '/' + 'objdetect.jpg')
            objdetect_image = cv2.circle(objdetect, center_coordinates, radius, color, thickness=-1) 
            objdetect_res = cv2.imwrite(self.EventFilePath + '/' + 'objdetect.jpg', objdetect_image)

            path_and_filename = f'{self.EventFilePath}/zone_{number}.jpg'
            try:
                result = cv2.imwrite(path_and_filename, alarm_image)
            except Exception as all_ex:
                self.g.logger.error(
                    f"{lp} ERROR writing image event folders -> {all_ex}")
            else:
                try:
                    chown(path_and_filename, webuser, webgroup)
                except Exception as all_ex:
                    self.g.logger.error(
                        f"{lp} ERROR writing image event folders -> {all_ex}")


    def ObjLocation_save_images(self) -> location:
        """
        save images of object in or outside of zones
        """

        # Warning dots on the image based on the calculated location
        if self.warning_dots_draw(self.location_list) != True:
            self.g.logger.debug( 4,
                f"{lp} Error drawing warning dots on image")

        # Stores the image on the local file system / event folder 
        if self.zones_images_save() != True:
            self.g.logger.debug( 4,
                f"{lp} Error storing images of zones")
        else:
            self.g.logger.debug( 4,
                f"{lp} Zone images stored successfully")

        return self.location_list


    def calc_location(self) -> location:
        """
        Calculates the location of object bounding boxes within zones.
        """
        gray_level = 127
        one_zone = 1

        self.location_zone.clear()
        for object_bbox_counter, object_bbox, in enumerate(self.object_bboxes_list):

            blank_image = gray_level * np.ones(shape=(self.height, self.width, self.c), dtype=np.uint8)

            #pts = np.array(zones_pts, np.int32)    
            self._draw_polygon(blank_image, self.zone_coordinates)

            # get lenght of the object bounding box

            # convert image to a grayscale
            gray_scaled = cv2.cvtColor(blank_image, cv2.COLOR_BGR2GRAY)

            # thresholding the image
            thresh = cv2.threshold(gray_scaled, 125, 125, cv2.THRESH_BINARY_INV)[1]

            # find contours in thresholded image
            contours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours = imutils.grab_contours(contours)

            length_zone = cv2.contourArea(contours[0]) 

            self._draw_rectangle_color (blank_image, 
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

            if len(contours) == one_zone:
                # if the zone has increased in size
                if length_object > length_zone:
                    location_zone = self.location.partly_inside_zone
                else:
                    location_zone = self.location.inside_zone
            else:
                location_zone = self.location.outside_zone

            self.location_zone.append(location_zone)

            try:
                # draw original image and the overlay weighted
                self.image_weighted = cv2.addWeighted(self.image_obj, .6, image_contours, .9, 0)
            except Exception as all_ex:
                self.g.logger.error(
                    f"{lp} ERROR drawing image -> {all_ex}")

            self.image_list.append( dict ( image = self.image_weighted, loc =  location_zone))

        return self.location_zone


    def ObjLocationFilterDetections(self, box : list, label : list, frameID : int) -> location:
        """
        Performs the complete object location process
        """
        self.current_frameID = frameID
        self.bboxes = [box]
        self.labels = [label]

        # Read image from a FrameId. eg. image name "00173-capture.jpg"
        image_obj_name = str(frameID).zfill(5) + '-capture.jpg'
        self.image_obj = cv2.imread(self.EventFilePath + '/' + image_obj_name)

        # Queries the zone coordinates from the zm-api
        if self.get_zone_coordinates(self.MonitorID) != []:
            self.g.logger.debug( 4, 
                f"{lp} Zone coordinates: {self.zone_coordinates}")
        else:
            # Queries the zone coordinates from Inkscape file -> object_zone.html.
            if self.get_zone_coordinates_Inkscape_html(self.MonitorID) != []:
                self.g.logger.debug( 4, 
                    f"{lp} Zone coordinates Inkscape: {self.zone_coordinates}")
            else:
                self.g.error( 4, 
                    f"{lp} No zone coordinates of ZM-Api or Inkscape: {self.zone_coordinates}")

        # Retrieves the event data
        if self.get_event_sequence_detect_data() != []:
           self.g.logger.debug( 4,
               f"{lp} Object bounding boxes: {self.object_bboxes_list}")

        # Calculates the location of objects
        self.location_list = self.calc_location()
        if self.location_list != []:
            self.g.logger.debug( 4,
                f"{lp} Location list: {self.location_list}")

        return self.location_list


