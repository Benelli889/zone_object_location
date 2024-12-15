#!/usr/bin/python3

# . . . .

from pyzm.helpers.zone_obj_loc import ObjLocation

# . . . .
>>>>>>>>>>
# ObjLocation init
g.config['ObjLocation'] = ObjLocation(g, g.eid)
>>>>>>>>>>

# . . . .

    matched_data, all_data, all_frames = m.detect_stream(
        stream=Id, options=detect_stream_options, ml_overrides=ml_overrides,
        in_file=True if args_get else False
    )
        # . . . .

        if not args.get('file'):
            # check if we have written objects.json and see if the past detection is the same is this detection
            skip_write = None
            jf = f"{args.get('eventpath')}/objects.json"
            json_file_ = Path(jf)

            # . . . .

>>>>>>>>>>
            if str2bool( g.config['zone_object_detection_options'].get("zone_object_detection_images")):

                # get instance of object location
                obj_loc = g.config['ObjLocation']
                
                # store object and zone related images in the event folder
                ret_location_list = obj_loc.ObjLocation_save_images()
                
                # optional use: get the location of matched_data
                location_list = matched_data['zone_location']
                
                for zone_loc in location_list:
                    pass

                if ret_location_list != None:

                    # do specific alaming for each object in zone
                    pass
>>>>>>>>>>

