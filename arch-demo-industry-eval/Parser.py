from textx import metamodel_from_file

arch_meta = metamodel_from_file("arch.tx")

# architecture = arch_meta.model_from_file("example.arch")
architecture = arch_meta.model_from_file("textual.arch")

for comp in architecture.components:
    print("component: " + comp.name)
