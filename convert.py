import argparse
import json
import logging
import os
from datetime import datetime
import xml.etree.ElementTree as ET

def split_latlng(latlng):
    lat, lng = latlng.replace("Â°", "").split(",")
    return (float(lat.strip()), float(lng.strip()))

def dump_gpx(points, output_file):
    gpx = ET.Element("gpx", version="1.1", creator="Timeline2GPX")
    trk = ET.SubElement(gpx, "trk")
    name = ET.SubElement(trk, "name")
    name.text = "Timeline"
    trkseg = ET.SubElement(trk, "trkseg")

    for point in points:
        trkpt = ET.SubElement(trkseg, "trkpt", lat=str(point['latitude']), lon=str(point['longitude']))
        time = ET.SubElement(trkpt, "time")
        time.text = point['time'].isoformat()

    tree = ET.ElementTree(gpx)
    tree.write(output_file, encoding="UTF-8", xml_declaration=True)
    logging.info(f"Dumped {len(points)} points to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Convert an Android Timeline JSON file to a GPX track")
    parser.add_argument("-i", "--input", help="Input timeline JSON file", required=True, type=str)
    parser.add_argument("-o", "--output", help="Output GPX file", required=True, type=str)
    parser.add_argument("-c", "--count", help="Maximum number of points per track", type=int, default=-1)
    parser.add_argument("-d", "--days", help="Maximum of days to include in the track", type=int, default=-1)
    parser.add_argument("-s", "--start", help="Start date (YYYY-MM-DD)", default=None)
    parser.add_argument("-e", "--end", help="End date (YYYY-MM-DD)", default=None)
    parser.add_argument("-l", "--loglevel", help="Log level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)
    if os.path.exists(args.output):
        logging.error(f"Output file {args.output} already exists")
        return
    if not os.path.exists(args.input):
        logging.error(f"Input file {args.input} does not exist")
        return
    if os.path.basename(args.output) != args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)

    points = []

    output_number = 0
    def dump(points_to_dump):
        nonlocal output_number
        if len(points) > 0:
            if args.output.endswith(".gpx"):
                output_name = args.output.replace(".gpx", f"_{output_number:05}.gpx")
            else:
                output_name = f"{args.output}_{output_number:05}.gpx"
            dump_gpx(points_to_dump, output_name)
            output_number += 1


    with open(args.input, "r") as f:
        timeline = json.load(f)
        semantic_segments = timeline["semanticSegments"]
        logging.info(f"Found {len(semantic_segments)} semantic segments")
        for segment in semantic_segments:
            start_time = datetime.strptime(segment["startTime"], "%Y-%m-%dT%H:%M:%S.%f%z")
            end_time = datetime.strptime(segment["endTime"], "%Y-%m-%dT%H:%M:%S.%f%z")
            if "timelinePath" in segment.keys():
                logging.debug(f"Segment {start_time} - {end_time} is a path of {len(segment['timelinePath'])} points")
                for point in segment["timelinePath"]:
                    lat, lng = split_latlng(point["point"])
                    points.append({
                        "time": datetime.strptime(point["time"], "%Y-%m-%dT%H:%M:%S.%f%z"),
                        "latitude": lat,
                        "longitude": lng
                    })

            # if "visit" in segment.keys():
            #     logging.debug(f"Segment {start_time} - {end_time} is a place visit")
            #     lat, lng = split_latlng(segment["visit"]["topCandidate"]["placeLocation"]["latLng"])
            #     points.append({
            #         "time": start_time,
            #         "latitude": lat,
            #         "longitude": lng
            #     })
            # elif "activity" in segment.keys():
            #     logging.debug(f"Segment {start_time} - {end_time} is an activity")
            #     for point in segment["activity"]["waypoints"]:
            #         lat, lng = split_latlng(point["latLng"])
            #         points.append({
            #             "time": datetime.strptime(point["timestamp"], "%Y-%m-%dT%H:%M:%S.%f%z"),
            #             "latitude": lat,
            #             "longitude": lng
            #         })
    points = sorted(points, key=lambda x: x['time'])
    start = 0
    for i in range(1, len(points)):
        # Skip points that are before the start date
        if args.start is not None and points[i]['time'].date() < datetime.strptime(args.start, "%Y-%m-%d").date():
            start = i
            continue
        # Skip points that are after the end date
        if args.end is not None and points[i]['time'].date() > datetime.strptime(args.end, "%Y-%m-%d").date():
            break
        # Dump if we have reached the maximum number of points
        if args.count > 0 and i - start >= args.count:
            dump(points[start:i])
            start = i
        # Dump if we have reached the maximum number of days
        if args.days > 0 and (points[i]['time'].date() - points[start]['time'].date()).days >= args.days:
            dump(points[start:i])
            start = i
    dump(points[start:])

if __name__ == "__main__":
    main()