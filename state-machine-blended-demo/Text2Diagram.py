import os
import sys
import json
import re
from textx import metamodel_from_file
from DrawIO import *
from Helpers import *

metamodel_file = "sm.tx"


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


# Parse arguments
def parse_ars(args):
    if len(args) <= 1:
        print("Missing argument\n")
        display_help_text()
        print("Trying to continue with default\n")
        model_file = "trafficlightstatemachine.sm"
    elif not os.path.isfile(args[1]):
        print("File given as argument does not exist\n")
        display_help_text()
        print("Trying to continue with default\n")
        model_file = "trafficlightstatemachine.sm"
    else:
        model_file = args[1]
        
    return model_file


# read element to graphical xml element from file.
def read_element_to_xml_map_from_file(filename):
    element_to_xml_map_file = filename + ".text2graphmap"
    element_to_xml_map = {}
    if os.path.isfile(element_to_xml_map_file):
        with open(element_to_xml_map_file, 'r') as f:
            element_to_xml_map = json.load(f)
    
    return element_to_xml_map


# for writing textual model back, see if we have a legend
def load_legend():
    legend2xml = {}
    legend_to_xml_map_file = "legend2xml.map"
    if os.path.isfile(legend_to_xml_map_file):
        with open(legend_to_xml_map_file, 'r') as f:
            legend2xml = json.load(f)

    return legend2xml


# for maintaining textual layout too
def read_textual_model(model_file):
    with open(model_file, 'r') as f:
        all_lines_in_textual_file = f.readlines()

    return all_lines_in_textual_file


def get_lines(statemachine, element, prevline, all_lines_in_textual_file):
    element_to_text_map = {}
    if all_lines_in_textual_file:
        endline, endcol = statemachine._tx_parser.pos_to_linecol(element._tx_position_end)
        lines = []
        # prevline+1 because we start from 1 after previous
        # endline+1 because range is not inclusive
        for i in range(prevline + 1, endline + 1):
            # here index -1 because list index starts at 0 but file lines start at 1
            lines.append(all_lines_in_textual_file[i - 1])
        element_to_text_map[element.name] = lines
        prevline = endline

    return prevline, lines


# if a new node is added in textual repr, here we create a new node for it based on the template in the legend
def create_node_from_template(legend2xml, nr_added_elements, node_type, element):
    template_node = legend2xml[node_type]
    replacement_node = etree.fromstring(template_node)
    replacement_node.attrib['id'] = replacement_node.attrib['id'] + 'a' + str(nr_added_elements)
    replacement_node.attrib['value'] = element.name
    return etree.tostring(replacement_node).decode('utf-8')


# write the textual model back to the drawing file
# for maintaining textual layout, also store X_to_text_map
def create_graphical_model(statemachine, all_lines_in_textual_file, legend2xml, element_to_xml_map):
    element_to_text_map = {}
    new_xml_nodes = []
    prevline, prevcol = 0, 0
    nr_added_elements = 0

    # for each element, store textual layout and write graphical output
    # this is a bit of duplicated code, but I find it more readable like this
    if statemachine.initialstate:
        # store textual layout
        element_to_text_map['initialstates'] = {}
        prevline, element_to_text_map['initialstates'][statemachine.initialstate.name] = \
            get_lines(statemachine, statemachine.initialstate, prevline, all_lines_in_textual_file)

        # write graphical output
        # if exists in xml_map then take that one
        if statemachine.initialstate.name in element_to_xml_map['initialstates']:
            new_xml_nodes.append(element_to_xml_map['initialstates'][statemachine.initialstate.name])
        # else if "new" then create a node from the template from the legend file
        elif legend2xml and "initialstate" in legend2xml:
            new_xml_nodes.append(create_node_from_template(legend2xml, nr_added_elements, "initialstate", statemachine.initialstate))
            nr_added_elements = nr_added_elements + 1

    if statemachine.finalstate:
        # store textual layout
        element_to_text_map['finalstates'] = {}
        prevline, element_to_text_map['finalstates'][statemachine.finalstate.name] = \
            get_lines(statemachine, statemachine.finalstate, prevline, all_lines_in_textual_file)

        # write graphical output
        # if exists in xml_map then take that one
        if statemachine.finalstate.name in element_to_xml_map['finalstates']:
            new_xml_nodes.append(element_to_xml_map['finalstates'][statemachine.finalstate.name])
        # if not in original drawing, create from legend
        elif legend2xml and "finalstate" in legend2xml:
            new_xml_nodes.append(create_node_from_template(legend2xml, nr_added_elements, "finalstate", statemachine.finalstate))
            nr_added_elements = nr_added_elements + 1

    if statemachine.states:
        # store textual layout
        element_to_text_map['intermediatestates'] = {}
        prevline = find_line_with_language_keyword("IntermediateStates {", all_lines_in_textual_file)
        for intermediatestate in statemachine.states:
            # store textual layout
            prevline, element_to_text_map['intermediatestates'][intermediatestate.name] = \
                get_lines(statemachine, statemachine.finalstate, prevline, all_lines_in_textual_file)

            # write graphical output
            # if exists in xml_map then take that one
            if intermediatestate.name in element_to_xml_map['intermediatestates']:
                new_xml_nodes.append(element_to_xml_map['intermediatestates'][intermediatestate.name])
            # if not in original drawing, create from legend
            elif legend2xml and "intermediatestate" in legend2xml:
                new_xml_nodes.append(create_node_from_template(legend2xml, nr_added_elements, "intermediatestate", intermediatestate))
                nr_added_elements = nr_added_elements + 1

    if statemachine.transitions:
        element_to_text_map['transitions'] = {}
        prevline = find_line_with_language_keyword("Transitions {", all_lines_in_textual_file)
        for transition in statemachine.transitions:
            # store textual layout
            prevline, element_to_text_map['transitions'][transition.name] = \
                get_lines(statemachine, transition, prevline, all_lines_in_textual_file)

            # write graphical output
            # if exists, write it, but make sure we take condition and action from the textual repr.
            if transition.name in element_to_xml_map['transitions']:
                transition_xml_str = element_to_xml_map['transitions'][transition.name]
                transition_xml = etree.fromstring(transition_xml_str)
                val_str = transition_xml.get("value")
                condition_str = re.search('.*\[(.*)\].*',val_str).group(1)
                val_str = val_str.replace(condition_str, transition.condition)
                action_str = val_str.split("/", 1)[1]
                val_str = val_str.replace(action_str, transition.action)
                transition_xml.attrib['value'] = val_str
                replacement_transition_xml_str = etree.tostring(transition_xml).decode('utf-8')
                new_xml_nodes.append(replacement_transition_xml_str)

            elif legend2xml and "transition" in legend2xml:
                # adding "from legend"; for now, this is implemented with knowledge that this is an edge
                template_edge = legend2xml["transition"]
                replacement_edge = etree.fromstring(template_edge)

                replacement_edge.attrib['id'] = replacement_edge.attrib['id'] + 'a' + str(nr_added_elements)
                nr_added_elements = nr_added_elements + 1

                replacement_value = replacement_edge.get("value")
                # first remove the metamodel element name, then replace the other keywords
                replacement_value = replacement_value.replace("transition", "", 1)
                transition_keywords = ['name', 'condition', 'action']
                for keyword in transition_keywords:
                    if keyword in replacement_edge.get("value"):
                        replacement_value = replacement_value.replace(keyword, getattr(transition, '%s' % keyword))

                replacement_edge.attrib['value'] = replacement_value
                print("replaced: " + replacement_edge.attrib['value'])

                # Setting source (needs the id of source node in the xml, so can't create complete new one)
                if has_source(replacement_edge):
                    source_keywords = ['initialstatetransition', 'enterstate']
                    for keyword in source_keywords:
                        source_state = getattr(transition, '%s' % keyword)
                        if source_state is not None:
                            source_id = None
                            if source_state.name == statemachine.initialstate.name:
                                source_id = get_id_of_element(source_state, new_xml_nodes)
                            else:
                                for state in statemachine.states:
                                    if source_state.name == state.name:
                                        source_id = get_id_of_element(state, new_xml_nodes)
                                        break
                            if source_id is not None:
                                replacement_edge.attrib['source'] = source_id

                # Setting target (needs the id of target node in the xml, so can't create complete new one)
                if has_target(replacement_edge):
                    target_keywords = ['finalstatetransition', 'exitstate']
                    for keyword in target_keywords:
                        target_state = getattr(transition, '%s' % keyword)
                        if target_state is not None:
                            target_id = None
                            if target_state.name == statemachine.finalstate.name:
                                target_id = get_id_of_element(target_state, new_xml_nodes)
                            else:
                                for state in statemachine.states:
                                    if target_state.name == state.name:
                                        target_id = get_id_of_element(state, new_xml_nodes)
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
    semantic_shape_types = [ShapeType.INITIALSTATE, ShapeType.FINALSTATE, ShapeType.INTERMEDIATESTATE, ShapeType.TRANSITION]
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
    metamodel = metamodel_from_file(metamodel_file)
    statemachine = metamodel.model_from_file(model_file)

    element_to_xml_map = read_element_to_xml_map_from_file(filename)
    legend2xml = load_legend()
    all_lines_in_textual_file = read_textual_model(model_file)

    element_to_text_map, new_xml_nodes = create_graphical_model(statemachine, all_lines_in_textual_file, legend2xml, element_to_xml_map)
    write_graphical_model_to_file(filename, new_xml_nodes)
    persist_model_element_to_text_element_map(filename, element_to_text_map)

    print("done")


if __name__ == "__main__":
    main()
