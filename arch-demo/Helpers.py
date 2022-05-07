def find_line_with_language_keyword(keywordstr, all_lines_in_file):
    if not all_lines_in_file:
        return 0
    else:
        for i in range(0, len(all_lines_in_file)):
            if all_lines_in_file[i].strip() == keywordstr:
                return i+1
    return 0


def get_dependency_key(dep):
    if type(dep) is dict:
        return f"_=from=_{dep['from']}_=to=_{dep['to']}"
    else:
        return f"_=from=_{dep.fromcomp.name}_=to=_{dep.tocomp.name}"


# def get_dict_from_dependency_key(dep_key):
#    dependency={}
#    fromto = dep_key.split("_=to=_",1)
#    dependency["from"] = fromto[0].split("_=from=_", 1)[1]
#    dependency["to"] = fromto[1]
#    return dependency
