import os
import sys
import json
from DrawIO import *

legend_to_XML_map_file = "legend2xml.map"


def display_help_text():
    print("Usage: python Legend2Map.py [file]\nfile\t: name of .drawio file to parse\n")
    print("The purpose of this script is to parse a drawio file containing a 'legend' for graphical components.\n")
    print("The result of the script is a map file that knows for a certain model element how to draw it.\n")
    print("For example: 'component' maps to an XML snippet showing a component box\n")


def parse_args(args):
    # Parse argument
    if len(args) <= 1:
        print("Missing argument\n")
        display_help_text()
        print("Trying with default: legend.drawio")
        legend_file = "legend.drawio"
    # Check if argument file exists
    elif not os.path.isfile(args[1]):
        print("File given as argument does not exist\n")
        display_help_text()
        print("Trying with default: legend.drawio")
        legend_file = "legend.drawio"
    else:
        legend_file = args[1]

    return legend_file


# get shapes from the drawing and create a map of concept2xml fragment
def get_shapes_from_drawing(xml_string):
    all_shapes = get_all_shapes(xml_string)
    legend2shape = {}
    for shape in all_shapes:
        legend2shape[shape.get("value")] = etree.tostring(shape).decode('utf-8')

    return legend2shape


# same as for Drawing2Text, persist the map to file
def persist_map_to_file(legend2shape, filename):
    with open(filename, 'w') as f:
        json.dump(legend2shape, f)
    print(f"wrote legend to xml mapping: {filename}")


def main():
    legend_file = parse_args(sys.argv)

    # read files
    xml_string = get_xml_string_from_file(legend_file)

    legend2shape = get_shapes_from_drawing(xml_string)
    persist_map_to_file(legend2shape, legend_to_XML_map_file)

    print("done")


if __name__ == "__main__":
    main()
