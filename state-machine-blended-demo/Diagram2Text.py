import json
import sys
import os
from DrawIO import *


class Transition(object):
    def __init__(self, name, condition, action, enterstate, existate, is_initialstate_transition, is_finalstate_transition):
        self.name = name
        self.condition = condition
        self.action = action
        self.enterstate = enterstate
        self.exitstate = existate
        self.is_initialstate_transition = is_initialstate_transition
        self.is_finalstate_transition = is_finalstate_transition


def display_help_text():
    print("Usage: python Diagram2Text.py [file]\nfile\t: name of .drawio file to parse")
    print("This script parses the statemachine drawing into a textual model.")
    print("Additionally, a .map file is persisted to restore the graphical view after changes to the textual model.\n")


def print_if_exists_else(file, frommap, submapkey, key, alternative_text):
    if not submapkey == "" and frommap:
        if submapkey in frommap:
            for thisline in frommap[submapkey][key]:
                file.write(thisline)
        else:
            file.write(alternative_text)
    else:
        file.write(alternative_text)


def parse_args(args):
    if len(args) <= 1:
        print("Missing argument\n")
        display_help_text()
        print("Continuing with default: trafficlightstatemachine.drawio")
        drawing_file = "trafficlightstatemachine.drawio"
    # Check if argument file exists
    elif not os.path.isfile(args[1]):
        print("File given as argument does not exist\n")
        display_help_text()
        print("Continuing with default: trafficlightstatemachine.drawio")
        drawing_file = "trafficlightstatemachine.drawio"
    else:
        drawing_file = args[1]
        
    return drawing_file


# read elements of given shape_type, works for nodes.
def get_elements_from_drawing(xml_string, shape_type):
    elementtype_to_xml_map = {}
    elementtype_to_xml_string_map = {}
    for ellipse in get_shapes_of_exact_type(xml_string, shape_type):
        state = ellipse.get("value")
        elementtype_to_xml_map[state] = ellipse
        elementtype_to_xml_string_map[state] = etree.tostring(ellipse).decode('utf-8')

    return elementtype_to_xml_map, elementtype_to_xml_string_map


# building a textual model from drawing.
# at the same time, store the graphical information in a map<component, xml>
def build_model_from_drawing(xml_string):
    # this is in place of next few commented out lines
    elements_to_xml_map = {}
    elements_to_xml_string_map = {}
    elements_to_xml_map["initialstates"], elements_to_xml_string_map["initialstates"] = get_elements_from_drawing(xml_string, ShapeType.INITIALSTATE)
    elements_to_xml_map["intermediatestates"], elements_to_xml_string_map["intermediatestates"] = get_elements_from_drawing(xml_string, ShapeType.INTERMEDIATESTATE)
    elements_to_xml_map["finalstates"], elements_to_xml_string_map["finalstates"] = get_elements_from_drawing(xml_string, ShapeType.FINALSTATE)

    # read transitions and contained elements
    transitions_to_xml_map = {}
    transitions_to_xml_string_map = {}
    transition_objs = {}
    transitions = get_shapes_of_type(xml_string, ShapeType.TRANSITION)
    for arrow in transitions:
        label = arrow.get("value")
        transition = (label.split('('))[1].split(')')[0]
        transitions_to_xml_map[transition] = etree.tostring(arrow).decode('utf-8')
        transitions_to_xml_string_map[transition] = etree.tostring(arrow).decode('utf-8')
        condition = (label.split('['))[1].split(']')[0]
        action = (label.split('/'))[1]
        transition_obj = Transition(transition, condition, action, None, None, False, False)

        # find enter and exit state
        sourceid = arrow.get("source")
        targetid = arrow.get("target")
        # here changed _to_xml_string_ to just _to_xml_ (for two following lines)
        for statetype in elements_to_xml_map:
            for state, statexml in elements_to_xml_map[statetype].items():
                if statexml.get("id") == sourceid:
                    if is_of_type(statexml, ShapeType.INITIALSTATE):
                        transition_obj.is_initialstate_transition = True
                    transition_obj.enterstate = state
                if statexml.get("id") == targetid:
                    if is_of_type(statexml, ShapeType.FINALSTATE):
                        transition_obj.is_finalstate_transition = True
                    transition_obj.exitstate = state

        transition_objs[transition] = transition_obj

    elements_to_xml_map["transitions"] = transitions_to_xml_map
    elements_to_xml_string_map["transitions"] = transitions_to_xml_string_map

    return transition_objs, elements_to_xml_map, elements_to_xml_string_map


# read the textual information from file
# for possible usage in writing back the graphical elements
# (if known from before, preserve previous textual syntax)
def read_elements_to_text_map(filename):
    elements_to_text_map_file = filename + ".text2textmap"
    elements_to_text_map = {}
    if os.path.isfile(elements_to_text_map_file):
        with open(elements_to_text_map_file, 'r') as f:
            elements_to_text_map = json.load(f)

    return elements_to_text_map


# write textual model file
def write_textual_model_file(filename, transition_objs, elements_to_xml_map, elements_to_text_map):
    textual_model_file = filename + ".sm"
    file = open(textual_model_file, 'w')
    for initialstate in elements_to_xml_map["initialstates"]:
        print_if_exists_else(file, elements_to_text_map, "initialstates", initialstate, f"InitialState {initialstate}\n")

    for finalstate in elements_to_xml_map["finalstates"]:
        print_if_exists_else(file, elements_to_text_map, "finalstates", finalstate, f"FinalState {finalstate}\n")

    # write intermediatestates
    if elements_to_xml_map["intermediatestates"]:
        file.write("IntermediateStates {\n")

        index = 0
        nr_states = len(elements_to_xml_map["intermediatestates"])
        for intermediatestate in elements_to_xml_map["intermediatestates"]:
            if elements_to_text_map and "intermedatestates" in elements_to_text_map and intermediatestate in elements_to_text_map["intermediatestates"]:
                for line in elements_to_text_map["intermediatestates"][intermediatestate]:
                    file.write(line)
                index = index+1
            else:
                file.write(intermediatestate)
                index = index + 1
                if index < nr_states:
                    file.write(",")
            file.write("\n")

        # end of IntermediateState { }
        file.write("} \n")

    # now writing transitions, it will be even more troublesome
    # first see if we need at all to write them
    if elements_to_xml_map["transitions"]:
        file.write("Transitions {" + "\n")
        if "transitions" in elements_to_xml_map:
            index = 0
            nr_transitions = len(elements_to_xml_map["transitions"])
            for transition in elements_to_xml_map["transitions"]:
                if "transitions" in elements_to_text_map and transition in elements_to_text_map["transitions"]:
                    for line in elements_to_text_map["transitions"][transition]:
                        # TODO cleanup, here experimenting with overwriting "condition" and "action" strings if they are different in drawing
                        # TODO for a complete impl, you should also look at from/to states, but for now I'm leaving it out, assuming that then you change the name too
                        if "Condition " in line and transition in transition_objs:
                            condition_from_drawing = transition_objs[transition].condition
                            if line.split("Condition ", 1)[1].strip() != f'"{condition_from_drawing}"':
                                file.write(f'Condition "{condition_from_drawing}"\n')
                            else:
                                file.write(line)
                        elif "Action " in line and transition in transition_objs:
                            action_from_drawing = transition_objs[transition].action
                            if line.split("Action ", 1)[1].strip() != f'"{action_from_drawing}"':
                                file.write(f'Action "{action_from_drawing}"\n')
                            else:
                                file.write(line)
                        else:
                            file.write(line)
                    index = index+1
                else:
                    file.write(transition + "\n")
                    if transition in transition_objs:
                        transition_obj = transition_objs[transition]
                        file.write(f'Condition "{transition_obj.condition}"\n')
                        file.write(f'Action "{transition_obj.action}"\n')

                        if transition_obj.is_initialstate_transition:
                            file.write('InitialStateTransition ' + transition_obj.enterstate + "\n")
                        else:
                            file.write('EnterState ' + transition_obj.enterstate + "\n")
                        if transition_obj.is_finalstate_transition:
                            file.write('FinalStateTransition ' + transition_obj.exitstate)
                        else:
                            file.write('ExitState ' + transition_obj.exitstate)

                    # separator for next transition, but not for last
                    index = index + 1
                    if index < nr_transitions:
                        file.write(",\n\n")

        # end of Transitions {}
        file.write("\n}")

    file.close()
    print("wrote textual model file: " + filename + ".sm")


# persist component to graphical xml element to file.
def persist_component_to_graphical_xml_map(filename, elements_to_xml_map):
    elements_to_xml_map_file = filename + ".text2graphmap"
    with open(elements_to_xml_map_file, 'w') as f:
        json.dump(elements_to_xml_map, f)
    print("wrote mapping: " + filename + ".text2graphmap")


def main():
    drawing_file = parse_args(sys.argv)
    
    # read files
    filename, file_extension = os.path.splitext(drawing_file)
    xml_string = get_xml_string_from_file(drawing_file)

    transition_objs, elements_to_xml_map, elements_to_xml_string_map = build_model_from_drawing(xml_string)
    elements_to_text_map = read_elements_to_text_map(filename)

    write_textual_model_file(filename, transition_objs, elements_to_xml_map, elements_to_text_map)
    persist_component_to_graphical_xml_map(filename, elements_to_xml_string_map)

    print("done")
    

if __name__ == "__main__":
    main()
