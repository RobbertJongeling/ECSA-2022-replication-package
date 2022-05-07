import json
import sys
import os
from DrawIO import *


class Dependency(object):
    def __init__(self, fromcomp=None, tocomp=None):
        self.fromcomp = fromcomp
        self.tocomp = tocomp

    def get_key(self):
        if self.fromcomp is not None and self.tocomp is not None:
            return f"_=from=_{self.fromcomp}_=to=_{self.tocomp}"
        else:
            return "nullkey"


class Component(object):
    def __init__(self, name, geometry):
        self.name = name
        self.geometry = geometry
        self.inlayers = []


class Layer(object):
    def __init__(self, name, geometry):
        self.name = name
        self.geometry = geometry


def display_help_text():
    print("Usage: python Diagram2Text.py [file]\nfile\t: name of .drawio file to parse\n")
    print("This script parses the architecture drawing into a textual model.\n")
    print("Additionally, persists a .map file to restore the graphical view after changes to the textual model.\n")


def layers_are_the_same(list_of_layers_from_drawing, textual_layers_repr):
    if len(textual_layers_repr) < 3:
        return False

    # TODO implement this based on model content, not on this ugliness.
    layers_from_text = textual_layers_repr[2:len(textual_layers_repr)-1]
    stripped_layers_from_text = []
    for lyr in layers_from_text:
        stripped_layers_from_text.append(lyr.strip().split(',', 1)[0])

    for lyr in list_of_layers_from_drawing:
        if lyr not in stripped_layers_from_text:
            return False
    for lyr in stripped_layers_from_text:
        if lyr not in list_of_layers_from_drawing:
            return False

    return True


def parse_args(args):
    if len(args) <= 1:
        print("Missing argument\n")
        display_help_text()
        print("Continuing with default: arch-drawing.drawio")
        drawing_file = "arch-drawing.drawio"
    # Check if argument file exists
    elif not os.path.isfile(sys.argv[1]):
        print("File given as argument does not exist\n")
        display_help_text()
        print("Continuing with default: arch-drawing.drawio")
        drawing_file = "arch-drawing.drawio"
    else:
        drawing_file = sys.argv[1]

    return drawing_file


# read elements of given shape_type, works for shapes with a geometry.
def get_elements_from_drawing(xml_string, shape_type, class_constructor):
    elementtype_to_xml_map = {}
    elementtype_to_xml_string_map = {}
    element_objs = []
    for shape in get_shapes_of_type(xml_string, shape_type):
        element = shape.get("value")
        if element:
            elementtype_to_xml_map[element] = shape
            elementtype_to_xml_string_map[element] = etree.tostring(shape).decode('utf-8')
            geo = shape.findall('.//mxGeometry')[0]
            element_objs.append(class_constructor(element, {"x": geo.get("x"), "y": geo.get("y"), "width": geo.get("width"), "height": geo.get("height")}))

    return element_objs, elementtype_to_xml_map, elementtype_to_xml_string_map


# read edge elements of given shape_type,
# here we want to check arrows between components, hence the component_to_xml_map
def get_edge_elements_from_drawing(xml_string, shape_type, class_constructor, source_and_target_elements_map):
    elementtype_to_xml_map = {}
    elementtype_to_xml_string_map = {}
    element_objs = []

    for arrow in get_edges_of_type(xml_string, shape_type):
        # For the elements, we construct here dependency objects
        sourceid = arrow.get("source")
        targetid = arrow.get("target")
        element_obj = class_constructor()
        for comp, compxml in source_and_target_elements_map.items():
            if compxml.get("id") == sourceid:
                element_obj.fromcomp = comp
            if compxml.get("id") == targetid:
                element_obj.tocomp = comp

        # These arrows have no id/name in the textual repr, so we use from and to components to create a key
        elmt_key = element_obj.get_key()
        elementtype_to_xml_map[elmt_key] = arrow
        elementtype_to_xml_string_map[elmt_key] = etree.tostring(arrow).decode('utf-8')
        element_objs.append(element_obj)

    return element_objs, elementtype_to_xml_map, elementtype_to_xml_string_map


# building a textual model from drawing
# at the same time, store the graphical information in a map<component, xml>
def build_model_from_drawing(xml_string):
    elements_to_xml_map = {}
    elements_to_xml_string_map = {}
    
    # read all the components
    component_objs, elements_to_xml_map["components"], elements_to_xml_string_map["components"] = \
        get_elements_from_drawing(xml_string, ShapeType.RECTANGLE, globals()["Component"])
    
    # read all the dependencies
    dependency_objs, elements_to_xml_map["dependencies"], elements_to_xml_string_map["dependencies"] = \
        get_edge_elements_from_drawing(xml_string, ShapeType.DEPENDENCY, globals()["Dependency"], elements_to_xml_map["components"])
    
    # read all the layers
    layer_objs, elements_to_xml_map["layers"], elements_to_xml_string_map["layers"] = \
        get_elements_from_drawing(xml_string, ShapeType.POLYGON, globals()["Layer"])
    
    # now that we have components and layers, we can check what component is in what layers
    for i in range(0, len(component_objs)):
        comp = component_objs[i]
        for lyr in layer_objs:
            if geometries_overlap(comp.geometry, lyr.geometry):
                comp.inlayers.append(lyr)
        component_objs[i] = comp

    return component_objs, dependency_objs, elements_to_xml_map, elements_to_xml_string_map


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
def write_textual_model_file(filename, elements_to_xml_map, elements_to_text_map, component_objs, dependency_objs):
    textual_model_file = filename + ".arch"
    file = open(textual_model_file, 'w')

    if "components" in elements_to_xml_map:
        file.write("components {" + "\n")
        index = 0
        nr_components = len(elements_to_xml_map["components"])

        for component in component_objs:
            # write textual repr in case we have it in elements_to_text_map
            write_new = True
            if elements_to_text_map and component.name in elements_to_text_map:
                # write what we have only if "inlayers" is unchanged, so
                # if component is not in layer in drawing and not in layer in text, write existing.
                # also if layers are the same, write existing.
                if (len(component.inlayers) == 0 and len(elements_to_text_map[component.name]) < 3) or \
                        (layers_are_the_same(component.inlayers, elements_to_text_map[component.name])):
                    for line in elements_to_text_map[component.name]:
                        file.write(line)
                    index = index+1
                    write_new = False

            if write_new:
                file.write("component " + component.name)
                if len(component.inlayers) > 0:
                    file.write("\n\tinlayers {\n")
                    inindex = 0
                    nr_inlayers = len(component.inlayers)
                    for lyr in component.inlayers:
                        file.write("\t\t" + lyr.name)

                        inindex = inindex + 1
                        if inindex < nr_inlayers:
                            file.write(",\n")
                    file.write("\n\t}")

                # print separator for next layer, but not for last
                index = index + 1
                if index < nr_components:
                    file.write(",\n")

        # end of Components {}
        file.write("\n}\n\n")

    if elements_to_xml_map["dependencies"]:
        file.write("dependencies {" + "\n")
        index = 0
        nr_dependencies = len(elements_to_xml_map["dependencies"])

        for dependency_obj in dependency_objs:
            dependency_key = dependency_obj.get_key()
            # write textual repr in case we have it in elements_to_text_map
            if elements_to_text_map and dependency_key in elements_to_text_map:
                for line in elements_to_text_map[dependency_key]:
                    file.write(line)
                index = index+1
            else:
                file.write(f"\tfrom {dependency_obj.fromcomp} to {dependency_obj.tocomp}")
                # print separator for next layer, but not for last
                index = index + 1
                if index < nr_dependencies:
                    file.write(",\n")

        # end of Dependencies {}
        file.write("\n}\n\n")

    if elements_to_xml_map["layers"]:
        file.write("layers {" + "\n")
        index = 0
        nr_layers = len(elements_to_xml_map["layers"])

        for layer in elements_to_xml_map["layers"]:
            # write textual repr in case we have it in elements_to_text_map
            if elements_to_text_map and layer in elements_to_text_map:
                for line in elements_to_text_map[layer]:
                    file.write(line)
                index = index+1
            else:
                file.write("\tlayer " + layer)
                # print separator for next layer, but not for last
                index = index + 1
                if index < nr_layers:
                    file.write(",\n")

        # end of Layers {}
        file.write("\n}\n")

    file.close()
    print(f"wrote textual model file: {filename}.arch")


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

    component_objs, dependency_objs, elements_to_xml_map, elements_to_xml_string_map = \
        build_model_from_drawing(xml_string)
    elements_to_text_map = read_elements_to_text_map(filename)
    
    write_textual_model_file(filename, elements_to_xml_map, elements_to_text_map, component_objs, dependency_objs)
    persist_component_to_graphical_xml_map(filename, elements_to_xml_string_map)

    print("done")


if __name__ == "__main__":
    main()

