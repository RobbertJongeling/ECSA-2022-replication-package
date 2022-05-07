import os
import sys
import json
from textx import metamodel_from_file
from DrawIO import *
from Helpers import *

metamodel_file = "arch-ext.tx"


# gets xml id of an input model element
def get_id_of_element(element, new_xml_nodes):
    for node in new_xml_nodes:
        nodexml = etree.fromstring(node)
        if element.name == nodexml.get("value"):
            return nodexml.get("id")

    return None


def display_help_text():
    print("Usage: python Text2Diagram.py [file]\nfile\t: name of .arch file to parse\n")
    print("The purpose of this script is to parse the textual model and regenerate the graphical view.\n")
    print("To do so, it relies on a stored -text2graph.map file which was generated during Diagram2Text.py\n")
    print("Hence, this can not work without first doing Drawing2Text\n")


# Parse argument
def parse_ars(args):
    if len(args) <= 1:
        print("Missing argument\n")
        display_help_text()
        print("Continuing with default: arch-drawing.arch")
        model_file = "arch-drawing.arch"
    # Check if argument file exists
    elif not os.path.isfile(args[1]):
        print("File given as argument does not exist\n")
        display_help_text()
        print("Continuing with default: arch-drawing.arch")
        model_file = "arch-drawing.arch"
    else:
        model_file = args[1]

    return model_file


# read component to graphical xml element from file.
def read_element_to_xml_map_from_file(filename):
    element_to_xml_map_file = filename + ".text2graphmap"
    element_to_xml_map = {}
    if os.path.isfile(element_to_xml_map_file):
        with open(element_to_xml_map_file, 'r') as f:
            element_to_xml_map = json.load(f)

    return element_to_xml_map


# for writing textual model back, see if we have a legend
def load_legend():
    legend_to_xml_map_file = "legend2xml.map"
    if os.path.isfile(legend_to_xml_map_file):
        with open(legend_to_xml_map_file, 'r') as f:
            legend2xml = json.load(f)
            
    return legend2xml


# for maintaining textual layout too
def read_textual_model(model_file):
    all_lines_in_textual_file = []
    with open(model_file, 'r') as f:
        all_lines_in_textual_file = f.readlines()
    return all_lines_in_textual_file


# write the textual model back to the drawing file
# for maintaining textual layout, also store element_to_text_map
def create_graphical_model(architecture, all_lines_in_textual_file, legend2xml, element_to_xml_map):
    element_to_text_map = {}
    new_xml_nodes = []
    prevline, prevcol = 0, 0
    nr_added_elements = 0

    # for each element, store textual layout and write graphical output
    # here we start with layers because the occurrence order of elements in the file determines the Z-order in the drawing
    if architecture.layers:
        # store textual layout
        prevline = find_line_with_language_keyword("layers {", all_lines_in_textual_file)

        for layer in architecture.layers:
            # store textual layout
            if all_lines_in_textual_file:
                endline, endcol = architecture._tx_parser.pos_to_linecol(layer._tx_position_end)
                lines = []
                # prevline+1 because we start from 1 after previous
                # endline+1 because range is not inclusive
                for i in range(prevline + 1, endline + 1):
                    # here index -1 because list index starts at 0 but file lines start at 1
                    lines.append(all_lines_in_textual_file[i - 1])
                element_to_text_map[layer.name] = lines
                prevline = endline

            # write graphical output, first check if we have it persisted
            if "layers" in element_to_xml_map and layer.name in element_to_xml_map["layers"]:
                new_xml_nodes.append(element_to_xml_map["layers"][layer.name])
            # text2graph for new layers
            elif legend2xml and "layer" in legend2xml:
                template_layer = legend2xml["layer"]
                replacement_layer = etree.fromstring(template_layer)
                # preventing id collissions
                replacement_layer.attrib['id'] = replacement_layer.attrib['id'] + 'a' + str(nr_added_elements)
                nr_added_elements = nr_added_elements + 1

                replacement_layer.attrib['value'] = layer.name
                replacement_layer = etree.tostring(replacement_layer).decode('utf-8')
                new_xml_nodes.append(replacement_layer)


    if architecture.components:
        # we want to exclude the DSL keyword "components {" from this.
        # TODO change to rely on line number of "components {" based on parsed model,
        #  rather than string search which can easily fail (also for dependencies and layers)
        prevline = find_line_with_language_keyword("components {", all_lines_in_textual_file)
        for component in architecture.components:
            # store textual layout
            if all_lines_in_textual_file:
                endline, endcol = architecture._tx_parser.pos_to_linecol(component._tx_position_end)
                lines = []
                # prevline+1 because we start from 1 after previous
                # endline+1 because range is not inclusive
                for i in range(prevline+1, endline+1):
                    # here index -1 because list index starts at 0 but file lines start at 1
                    lines.append(all_lines_in_textual_file[i-1])
                element_to_text_map[component.name] = lines
                prevline = endline

            # write graphical output
            if element_to_xml_map and component.name in element_to_xml_map["components"]:
                new_xml_nodes.append(element_to_xml_map["components"][component.name])
            # if new, then we have to create it
            elif legend2xml and "component" in legend2xml:
                template_node = legend2xml["component"]
                replacement_node = etree.fromstring(template_node)

                replacement_node.attrib['id'] = replacement_node.attrib['id'] + 'a' + str(nr_added_elements)
                nr_added_elements = nr_added_elements + 1

                replacement_node.attrib['value'] = component.name

                # TODO then here you'd need to do some magic to do the "inlayer" to graphical
                # I will do like this, every center point of every layer gets added to a list
                # Then, I will change the dimensions and location of this component so that it includes all those points
                points_to_cover = []
                if component.layers:
                    for layer in component.layers:
                        points_to_cover.append(get_center(element_to_xml_map["layers"][layer.name]))

                if points_to_cover:
                    replacement_node = create_spanning_element(replacement_node, points_to_cover)

                replacement_node = etree.tostring(replacement_node).decode('utf-8')
                new_xml_nodes.append(replacement_node)

    if architecture.dependencies:
        prevline = find_line_with_language_keyword("dependencies {", all_lines_in_textual_file)
        for dep in architecture.dependencies:
            dep_key = get_dependency_key(dep)

            # store textual layout
            if all_lines_in_textual_file:
                endline, endcol = architecture._tx_parser.pos_to_linecol(dep._tx_position_end)
                lines = []
                # prevline+1 because we start from 1 after previous
                # endline+1 because range is not inclusive
                for i in range(prevline+1, endline+1):
                    # here index -1 because list index starts at 0 but file lines start at 1
                    lines.append(all_lines_in_textual_file[i-1])
                element_to_text_map[dep_key] = lines
                prevline = endline

            # write graphical output, first check if we have it persisted
            if element_to_xml_map["dependencies"] and dep_key in element_to_xml_map["dependencies"]:
                new_xml_nodes.append(element_to_xml_map["dependencies"][dep_key])
            else:
                # tetx2graph for new dependencies")
                if legend2xml and "dependency" in legend2xml:
                    template_edge = legend2xml["dependency"]
                    replacement_edge = etree.fromstring(template_edge)

                    replacement_edge.attrib['id'] = replacement_edge.attrib['id'] + 'a' + str(nr_added_elements)
                    nr_added_elements = nr_added_elements + 1
                    # since these are "nameless", remove the value
                    replacement_edge.attrib['value'] = ""

                    # Setting source (Needs the id of source not in the xml)
                    source_id = None
                    if has_source(replacement_edge):
                        source_comp = dep.fromcomp
                        if source_comp is not None:
                            # lookup xml id for it
                            for comp in architecture.components:
                                if source_comp.name == comp.name:
                                    source_id = get_id_of_element(comp, new_xml_nodes)
                                    break
                    if source_id is not None:
                        replacement_edge.attrib['source'] = source_id

                    # Setting target (Needs the id of source not in the xml)
                    target_id = None
                    if has_target(replacement_edge):
                        target_comp = dep.tocomp
                        if target_comp is not None:
                            # lookup xml id for it
                            for comp in architecture.components:
                                if target_comp.name == comp.name:
                                    target_id = get_id_of_element(comp, new_xml_nodes)
                                    break
                    if target_id is not None:
                        replacement_edge.attrib['target'] = target_id

                    # That information is stored as a child node of the xml element
                    replacement_edge = etree.tostring(replacement_edge).decode('utf-8')
                    new_xml_nodes.append(replacement_edge)

    return element_to_text_map, new_xml_nodes


# writing to file
def write_graphical_model_to_file(filename, new_xml_nodes):
    path = filename + ".drawio"
    semantic_shape_types = [ShapeType.RECTANGLE, ShapeType.POLYGON, ShapeType.DEPENDENCY]
    replace_shapes_in_file(path, new_xml_nodes, semantic_shape_types)
    print("wrote drawing: " + path)


# persist textual syntax to file
def persist_model_element_to_text_element_map(filename, element_to_text_map):
    element_to_text_map_file = filename + ".text2textmap"
    with open(element_to_text_map_file, 'w') as f:
        json.dump(element_to_text_map, f)
    print("wrote mapping: " + filename + ".text2textmap")


def main():
    model_file = parse_ars(sys.argv)

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
