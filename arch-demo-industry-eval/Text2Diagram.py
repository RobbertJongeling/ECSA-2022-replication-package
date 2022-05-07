import os
import sys
import json
from textx import metamodel_from_file
from DrawIO import *

metamodel_file = "arch.tx"
legend_to_xml_map_file = "legend2xml.map"


def display_help_text():
    print("Usage: python Text2Diagram.py [file]\nfile\t: name of .arch file to parse\n")
    print("The purpose of this script is to parse the textual model and regenerate the graphical view.\n")
    print("To do so, it relies on a stored -text2graph.map file which was generated during Diagram2Text.py\n")
    print("Hence, this can not work without first doing Drawing2Text\n")


def parse_args(args):
    # Parse argument
    if len(args) <= 1:
        print("Missing argument\n")
        display_help_text()
        print("Trying with default: arch-drawing.drawio")
        model_file = "arch-drawing.arch"

    # Check if argument file exists
    elif not os.path.isfile(args[1]):
        print("File given as argument does not exist\n")
        display_help_text()
        print("Trying with default: arch-drawing.drawio")
        model_file = "arch-drawing.arch"
    else:
        model_file = args[1]

    return model_file


# read component to graphical xml element from file.
def read_element_to_xml_map_from_file(filename):
    component_to_xml_map_file = filename + ".text2graphmap"
    component_to_xml_map = {}
    if os.path.isfile(component_to_xml_map_file):
        with open(component_to_xml_map_file, 'r') as f:
            component_to_xml_map = json.load(f)

    return component_to_xml_map


# for writing textual model back, see if we have a legend
def load_legend():
    legend2xml = None
    if os.path.isfile(legend_to_xml_map_file):
        with open(legend_to_xml_map_file, 'r') as f:
            legend2xml = json.load(f)
    return legend2xml


# for maintaining textual layout too
def read_textual_model(model_file):
    with open(model_file, 'r') as f:
        all_lines_in_textual_file = f.readlines()
    return all_lines_in_textual_file


# return lines in textual model between last model element and this model element
def get_lines(architecture, component, prevline, all_lines_in_textual_file):
    endline, endcol = architecture._tx_parser.pos_to_linecol(component._tx_position_end)
    lines = []
    # prevline+1 because we start from 1 after previous
    # endline+1 because range is not inclusive
    for i in range(prevline + 1, endline + 1):
        # here index -1 because list index starts at 0 but file lines start at 1
        lines.append(all_lines_in_textual_file[i - 1])
    return endline, lines


# creates new node based on template from the legend
# change id to avoid duplicate ids and set name to component's name
def create_node_from_template(legend2xml, nr_added_elements, component):
    template_node = legend2xml["component"]
    replacement_node = etree.fromstring(template_node)

    replacement_node.attrib['id'] = f"{replacement_node.attrib['id']}a{nr_added_elements}"
    replacement_node.attrib['value'] = component.name

    return etree.tostring(replacement_node).decode('utf-8')


# write the textual model back to the drawing file
# for maintaining textual layout, also store component_to_text_map
def create_graphical_model(architecture, all_lines_in_textual_file, legend2xml, component_to_xml_map):
    component_to_text_map = {}
    new_xml_nodes = []
    prevline, prevcol = 0, 0
    nr_added_elements = 0

    # for each component, write graphical output and store textual layout information too
    for component in architecture.components:
        if all_lines_in_textual_file:
            prevline, component_to_text_map[component.name] = get_lines(architecture, component, prevline, all_lines_in_textual_file)

        # write graphical output
        # if exists in xml_map then take that one
        if component_to_xml_map and component.name in component_to_xml_map:
            new_xml_nodes.append(component_to_xml_map[component.name])
        # else if "new" then create a node from the template from the legend file
        elif legend2xml and "component" in legend2xml:
            new_xml_nodes.append(create_node_from_template(legend2xml, nr_added_elements, component))
            nr_added_elements = nr_added_elements + 1

    return component_to_text_map, new_xml_nodes


# writing to file
def write_graphical_model_to_file(filename, new_xml_nodes):
    semantic_shape_types = [ShapeType.RECTANGLE]
    replace_shapes_in_file(filename + ".drawio", new_xml_nodes, semantic_shape_types)
    print(f"wrote drawing: {filename}.drawio")


# persist textual syntax to map file
def persist_model_element_to_text_element_map(filename, element_to_text_map):
    element_to_text_map_file = filename + ".text2textmap"
    with open(element_to_text_map_file, 'w') as f:
        json.dump(element_to_text_map, f)
    print(f"wrote mapping:{filename}.text2textmap")


def main():
    model_file = parse_args(sys.argv)

    # read files
    filename, file_extension = os.path.splitext(model_file)
    arch_meta = metamodel_from_file(metamodel_file)
    architecture = arch_meta.model_from_file(model_file)

    element_to_xml_map = read_element_to_xml_map_from_file(filename)
    legend2xml = load_legend()
    all_lines_in_textual_file = read_textual_model(model_file)

    element_to_text_map, new_xml_nodes = create_graphical_model(architecture, all_lines_in_textual_file, legend2xml, element_to_xml_map)
    write_graphical_model_to_file(filename, new_xml_nodes)
    persist_model_element_to_text_element_map(filename, element_to_text_map)

    print("done")


if __name__ == "__main__":
    main()
