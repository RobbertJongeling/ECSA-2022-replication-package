import base64
import zlib
from enum import Enum
from urllib.parse import unquote_to_bytes, quote
from lxml import etree


# This expresses the things needed to be found in <x> 'style="<x>"' for a cell to be of that shape_type
# There must be a better way of doing this, but for now it's fine
class ShapeType(Enum):
    RECTANGLE = 'rounded=0;'
    ELLIPSE = 'ellipse;'
    RHOMBUS = 'rhombus;'
    POLYGON = 'shape=mxgraph.basic.polygon;'
    TEXT = 'text;'


def get_xml_string_from_file(path):
    tree = etree.parse(path)
    raw_string = tree.find('diagram').text

    data = base64.b64decode(raw_string)
    xml = zlib.decompress(data, wbits=-15)
    return unquote_to_bytes(xml).decode('utf-8')


def compress_xml(xml):
    data = quote(xml.encode('utf-8'))
    data = bytes(data, 'utf-8')
    compressor = zlib.compressobj(-1, zlib.DEFLATED, -15, zlib.DEF_MEM_LEVEL, zlib.Z_DEFAULT_STRATEGY)
    data = compressor.compress(data) + compressor.flush()
    # make in format for the .drawio file
    return base64.b64encode(data).decode('utf-8')


def replace_diagram_in_file(path, new_xml):
    tree = etree.parse(path)
    root = tree.getroot()
    tree.find('diagram').text = new_xml
    etree.ElementTree(root).write(path, pretty_print=True)


def get_all_shapes(drawio_xml_string):
    root = etree.fromstring(drawio_xml_string)
    shapes = root.findall('.//mxCell')
    to_return = []
    for shape in shapes:
        shape_id = shape.get("id")
        value = shape.get("value")
        style = shape.get("style")
        # ids 0 and 1 seem to be reserved for some internal structuring of the draw.io file
        if shape_id is not "0" and shape_id is not "1" and value is not None and style is not None:
            to_return.append(shape)
    return to_return


def get_shapes_of_type(drawio_xml_string, shape_type):
    root = etree.fromstring(drawio_xml_string)
    shapes = root.findall('.//mxCell')
    to_return = []
    for shape in shapes:
        value = shape.get("value")
        style = shape.get("style")
        # bit ugly testing for style, but I don't know how to get the style again as a dict
        if value is not None and style is not None and shape_type.value in style:
            to_return.append(shape)
    return to_return


# Here the idea is that the new_xml_nodes_for_shapes contains the new XML for the semantically relevant shapes
# All other shapes will be considered "comments" and will be kept it the drawing.
# But if there are in the drawing existing semantically relevant shapes that are not in the new_xml_nodes_for_shapes
# list, then those will not be included in the new diagram
def replace_shapes_in_file(path, new_xml_nodes_for_shapes, semantic_shape_types):
    complete_diagram_xml = get_xml_string_from_file(path)
    xml = etree.fromstring(complete_diagram_xml)

    # We delete only the shapes with semantically relevant types
    semantic_shapes_to_delete = []
    for shape_type in semantic_shape_types:
        semantic_shapes_to_delete.extend(get_shapes_of_type(complete_diagram_xml, shape_type))

    ids_to_delete = []
    for shape in semantic_shapes_to_delete:
        ids_to_delete.append(shape.get("id"))

    for node in xml.findall('root//'):
        if node.get("id") in ids_to_delete:
            node.getparent().remove(node)

    # Now add semantically relevant shapes again
    for node in new_xml_nodes_for_shapes:
        # The z-order of shapes in diagrams.net is decided by the order of the shapes in the XML
        # The system is first-come-first-drawn, so if we add all shapes at the beginning, they will all be hidden
        # TODO find a better solution than just appending things at the end
        xml.find('root').append(etree.fromstring(node))

    new_xml_string = etree.tostring(xml).decode('utf-8')

    # Now we can replace the diagram in the file with the new xml
    replace_diagram_in_file(path, compress_xml(new_xml_string))
