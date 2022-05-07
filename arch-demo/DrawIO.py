import base64
import zlib
from enum import Enum
from urllib.parse import unquote_to_bytes, quote
from lxml import etree
import shutil


# This expresses the things needed to be found in <x> 'style="<x>"' for a cell to be of that shape_type
# There must be a better way of doing this, but for now it's fine
class ShapeType(Enum):
    RECTANGLE = 'rounded=0;'
    SQUARE = 'whiteSpace=wrap;html=1;aspect=fixed;'  # yep I know, not great
    ELLIPSE = 'ellipse;'
    TRIANGLE = 'triangle;'
    RHOMBUS = 'rhombus;'
    POLYGON = 'mxgraph.basic.polygon;'
    TEXT = 'text;'
    INITIALSTATE = 'ellipse;whiteSpace=wrap;html=1;fontSize=10;fillColor=#666666;fontColor=#FFFFFF;'
    FINALSTATE = 'ellipse;whiteSpace=wrap;html=1;fontSize=10;'
    INTERMEDIATESTATE = 'ellipse;whiteSpace=wrap;html=1;fillColor=#f5f5f5;fontColor=#333333;strokeColor=#666666;'
    TRANSITION = 'rounded=0;orthogonalLoop=1;jettySize=auto;html=1;'
    DEPENDENCY = 'edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;'


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


def get_edges_of_type(drawio_xml_string, shape_type):
    root = etree.fromstring(drawio_xml_string)
    shapes = root.findall('.//mxCell')
    to_return = []
    for shape in shapes:
        style = shape.get("style")
        edge = shape.get("edge")
        # bit ugly testing for style, but I don't know how to get the style again as a dict
        if edge and style is not None and shape_type.value in style:
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


def get_shapes_of_exact_type(drawio_xml_string, shape_type):
    root = etree.fromstring(drawio_xml_string)
    shapes = root.findall('.//mxCell')
    to_return = []
    for shape in shapes:
        value = shape.get("value")
        style = shape.get("style")
        # bit ugly testing for style, but I don't know how to get the style again as a dict
        if value is not None and style is not None and shape_type.value == style:
            to_return.append(shape)
    return to_return


def is_of_type(style_xml, shape_type):
    style = style_xml.get("style")
    return style is not None and shape_type.value in style


# Here the idea is that the new_xml_nodes_for_shapes contains the new XML for the semantically relevant shapes
# All other shapes will be considered "comments" and will be kept it the drawing.
# But if there are in the drawing existing semantically relevant shapes that are not in the new_xml_nodes_for_shapes
# list, then those will not be included in the new diagram
def replace_shapes_and_save_to_new_file(path, new_path, new_xml_nodes_for_shapes, semantic_shape_types):
    complete_diagram_xml = get_xml_string_from_file(path)
    xml = etree.fromstring(complete_diagram_xml)

    # We delete only the shapes with semantically relevant types
    semantic_shapes_to_delete = []
    for shape_type in semantic_shape_types:
        semantic_shapes_to_delete.extend(get_shapes_of_type(complete_diagram_xml, shape_type))
        semantic_shapes_to_delete.extend(get_edges_of_type(complete_diagram_xml, shape_type))

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
    if path == new_path:
        replace_diagram_in_file(path, compress_xml(new_xml_string))
    else:
        shutil.copyfile(path, new_path)
        replace_diagram_in_file(new_path, compress_xml(new_xml_string))


# same as "replace_shapes_and
# _save_to_new_file" but in-place, save to same file.
def replace_shapes_in_file(path, new_xml_nodes_for_shapes, semantic_shape_types):
    replace_shapes_and_save_to_new_file(path, path, new_xml_nodes_for_shapes, semantic_shape_types)


# Return true if "vertex=1" in shape
def is_vertex(shape):
    try:
        val = shape.get("vertex")
    except:
        val = 0
    return val


# Return true if "edge=1" in shape
def is_edge(shape):
    try:
        val = shape.get("edge")
    except:
        val = 0
    return val


def has_source(shape):
    try:
        src = shape.get("source")
    except:
        src = 0
    return src is not None


def has_target(shape):
    try:
        src = shape.get("target")
    except:
        src = 0
    return src is not None


# returns True if A overlaps with B, else False.
def geometries_overlap(geometryA, geometryB):
    if not (geometryA["x"] is None or geometryA["y"] is None or geometryA["width"] is None or geometryA["height"] is None or
            geometryB["x"] is None or geometryB["y"] is None or geometryB["width"] is None or geometryB["height"] is None):
        bottom_left_a_x = float(geometryA["x"])
        bottom_left_a_y = float(geometryA["y"]) + float(geometryA["height"])
        top_right_a_x = float(geometryA["x"]) + float(geometryA["width"])
        top_right_a_y = float(geometryA["y"])
        bottom_left_b_x = float(geometryB["x"])
        bottom_left_b_y = float(geometryB["y"]) + float(geometryB["height"])
        top_right_b_x = float(geometryB["x"]) + float(geometryB["width"])
        top_right_b_y = float(geometryB["y"])

        # in the drawio coordinate system, (0,0) is topleft
        return not (top_right_a_x < bottom_left_b_x or
                    bottom_left_a_x > top_right_b_x or
                    top_right_a_y > bottom_left_b_y or
                    bottom_left_a_y < top_right_b_y)
    else:
        return False


# get center of element based on XML
def get_center(xml_element):
    element = etree.fromstring(xml_element)
    geos = element.findall('.//mxGeometry')
    # in the drawio coordinate system, (0,0) is topleft
    geo = geos[0]
    point = {"x": float(geo.get("x")) + float(geo.get("width")) / 2,
             "y": float(geo.get("y")) + float(geo.get("height")) / 2}
    return point


# returns same element but with dimensions stretched to cover all points in poinst_to_cover list
def create_spanning_element(element, points_to_cover):
    minx = None
    maxx = None
    miny = None
    maxy = None
    for point in points_to_cover:
        px = point.get("x")
        py = point.get("y")
        if minx is None or px < minx:
            minx = px
        if maxx is None or px > maxx:
            maxx = px
        if maxy is None or py > maxy:
            maxy = py
        if miny is None or py < miny:
            miny = py

    geos = element.findall('.//mxGeometry')
    print("debug, find out how to write new coordinates to element")
    for geo in geos:
        element.remove(geo)
        modified_geo = geo
        modified_geo.set("x", str(minx))
        modified_geo.set("y", str(miny))
        modified_geo.set("width", str(max(maxx - minx, 100)))
        modified_geo.set("height", str(max(maxy - miny, 50)))
        element.append(modified_geo)

    return element
