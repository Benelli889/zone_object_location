#!/usr/bin/python3

# . . .
>>>>>>>>>>
from pyzm.helpers.zone_obj_loc import ObjLocation
>>>>>>>>>>

# . . .

class DetectSequence:

# . . .

    # todo: clean up (kw)args
    def _filter_detections(
            self,
            model_name,
            box,
            label,
            conf,
            polygons,
            h,
            w,
            model_names,
            seq_opt=None,
            model_type=None,
            pkl_data=None,
    ):
        """INTERNAL METHOD. Filter out detected objects based upon configured options."""

    # . . .

>>>>>>>>>>
            # Check if the object pattern is inside the zone
            discard_image = False
            if str2bool(self.stream_options['zone_options'].get("zone_object_detection_enabled")):

                # optional use
                #obj_loc = ObjLocation(g, g.eid)

                obj_loc = g.config['ObjLocation']
                location_list = obj_loc.ObjLocationFilterDetections(box[idx], label[idx], self.media.last_frame_id_read)

                location_zone_set = {loc.value for loc in location_list}
                if (obj_loc.location.inside_zone.value in location_zone_set)                       or     \
                    ((obj_loc.location.partly_inside_zone.value in location_zone_set)              and    \
                    str2bool(self.stream_options['zone_options'].get("consider_partially_inside_zone")) == True):

                    discard_image = False
                    g.logger.debug(
                        f"{lp} Object pattern is inside zone {obj_loc.location.inside_zone.value}"
                    )
                else:
                    discard_image = True
                    g.logger.debug(
                        f"{lp} No object pattern inside zone {obj_loc.location.inside_zone.value}"
                    )

            if discard_image == True:
                continue
>>>>>>>>>>
            # end of main loop, if we made it this far label[idx] has passed filtering

            # . . .

>>>>>>>>>>
            new_location_zone = location_list
>>>>>>>>>>
        # . . .

        data = {
            "_b": new_bbox,
            "_l": new_label,
            "_c": new_conf,
            # . . .
>>>>>>>>>>
            "_z": new_location_zone,
>>>>>>>>>>
        }

        return data, extras
    
    # End of  _filter_detections ()

    # . . .


    # Run detection on a stream
    def detect_stream(self, stream, options=None, ml_overrides=None, in_file=False):

        # . . .

                            filtered_data, filtered_extras = self._filter_detections(
                                model_name,
                                _b,
                                _l,
                                _c,
                                polygons,
                                h,
                                w,
                            
                                # . . .

                            _b = filtered_data["_b"]
                            _l = filtered_data["_l"]
                            _c = filtered_data["_c"]
                            _e = filtered_data["_e"]
                            _m = filtered_data["_m"]
>>>>>>>>>>
                            _z = filtered_data["_z"]
                            
>>>>>>>>>>

    # . . .

            if found:
                all_matches.append(
                    {
                        "labels": _labels_in_frame,
                        "model_names": _model_names_in_frame,
                        "confidences": _confs_in_frame,
                        "detection_types": _detection_types_in_frame,
                        "frame_id": self.media.last_frame_id_read,
                        "boxes": _boxes_in_frame,
                        "error_boxes": _error_boxes_in_frame,
                        "image": frame.copy(),
>>>>>>>>>>
                        "zone_location": _z,
>>>>>>>>>>
                    }
                )

        # loop over camera pics END

        # find best match in all_matches
        for idx, item in enumerate(all_matches):

            # . . .

            ):
                matched_b = item["boxes"]
                # . . .

>>>>>>>>>>
                matched_z = item["zone_location"]
>>>>>>>>>>



        matched_data = {
            "labels": matched_l,
            # . . .
>>>>>>>>>>
            "zone_location": matched_z,
>>>>>>>>>>
        }

        return matched_data, all_matches, all_frames
