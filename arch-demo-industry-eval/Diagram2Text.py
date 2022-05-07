import json
import sys
import os
from DrawIO import *


def display_help_text():
    print("Usage: python Diagram2Text.py [file]\nfile\t: name of .drawio file to parse\n")
    print("This script lists all components in the architecture drawing and parses them into a textual model.\n")
    print("Additionally, a .map file is persisted to restore the graphical view after changes to the textual model.\n")


def parse_args(args):
    # Parse argument
    if len(args) <= 1:
        print("Missing argument\n")
        display_help_text()
        print("Trying with default: arch-drawing.drawio")
        drawing_file = "arch-drawing.drawio"
    # Check if argument file exists
    elif not os.path.isfile(args[1]):
        print("File given as argument does not exist\n")
        display_help_text()
        print("Trying with default: arch-drawing.drawio")
        drawing_file = "arch-drawing.drawio"
    else:
        # read drawing to xml
        drawing_file = args[1]

    return drawing_file


# building a simple model from drawing, assuming all rectangles are components
# at the same time, store the graphical information in a map<component, xml>
def build_model_from_drawing(xml_string):
    rectangles = get_shapes_of_type(xml_string, ShapeType.RECTANGLE)
    components = []
    component_to_xml_map = {}
    for rect in rectangles:
        component = rect.get("value")
        components.append(component)
        component_to_xml_map[component] = etree.tostring(rect).decode('utf-8')

    return components, component_to_xml_map


# read the textual information from file
def read_textual_model_from_file(filename):
    component_to_text_map_file = filename + ".text2textmap"
    component_to_text_map = {}
    if os.path.isfile(component_to_text_map_file):
        with open(component_to_text_map_file, 'r') as f:
            component_to_text_map = json.load(f)

    return component_to_text_map


# write textual model file
def write_textual_model_to_file(filename, components, component_to_text_map):
    textual_model_file = filename + ".arch"
    file = open(textual_model_file, 'w')
    for component in components:
        if component_to_text_map and component in component_to_text_map:
            for line in component_to_text_map[component]:
                file.write(line)
        else:
            file.write("component " + component + "\n")
    file.close()
    print("wrote textual model file: " + filename + ".arch")


# persist graphical sýntax to map file
def persist_model_element_to_graphical_element_map(filename, element_to_xml_map):
    # persist component to graphical xml element to file.
    element_to_xml_map_file = filename + ".text2graphmap"
    with open(element_to_xml_map_file, 'w') as f:
        json.dump(element_to_xml_map, f)
    print("wrote mapping: " + filename + ".text2graphmap")


def main():
    drawing_file = parse_args(sys.argv)

    # read files
    filename, file_extension = os.path.splitext(drawing_file)
    xml_string = get_xml_string_from_file(drawing_file)

    elements, element_to_xml_map = build_model_from_drawing(xml_string)
    element_to_text_map = read_textual_model_from_file(filename)

    write_textual_model_to_file(filename, elements, element_to_text_map)
    persist_model_element_to_graphical_element_map(filename, element_to_xml_map)

    print("done")


if __name__ == "__main__":
    main()
