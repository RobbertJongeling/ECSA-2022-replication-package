def find_line_with_language_keyword(keywordstr, all_lines_in_file):
    if not all_lines_in_file:
        return 0
    else:
        for i in range(0, len(all_lines_in_file)):
            if all_lines_in_file[i].strip() == keywordstr:
                return i+1
    return 0
