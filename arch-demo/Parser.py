# demo on how to extract information from the textual model and use it as objects in your code.
from textx import metamodel_from_file


class Architecture(object):
    def __init__(self, components, dependencies, layers):
        self.components = components
        self.dependencies = dependencies
        self.layers = layers


# here we load the grammar and parse the textual model
grammar = metamodel_from_file("arch-ext.tx", classes=[Architecture])
architecture = grammar.model_from_file("arch-drawing.arch")

# here we show how to access the fields
print("---printing components---")
for comp in architecture.components:
    print(comp.name + " in layers:")
    for layer in comp.layers:
        print(layer.name)

print("---printing layers---")
for layer in architecture.layers:
    print(layer.name + " contains components: ")
    for comp in architecture.components:
        for comp_in_layer in comp.layers:
            if layer.name == comp_in_layer.name:
                print(comp.name)

print("---printing dependencies---")
for dependency in architecture.dependencies:
    print(dependency.fromcomp.name + "-->" + dependency.tocomp.name)
