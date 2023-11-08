"""
Examples of NLG

"""
# *********************************************************************************************************************

# standard imports
import re

class HFNLG:
    """HumanFirst NLG related methods"""

    tag_name: str

    def __init__(self, tag_name: str):
        self.tag_name = tag_name

    def get_nlg_tag_regex(self) -> re:
        """Returns NLG tags REGEX"""

        hf_tag_list = ["conversation","text"]

        assert self.tag_name in hf_tag_list

        if self.tag_name == "conversation":
            return re.compile(r"{{[ ]*conversation[ ]*}}")
        elif self.tag_name == "text":
            return re.compile(r"{{[ ]*text[ ]*}}")
        else:
            raise KeyError(self.tag_name)
