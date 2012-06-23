from lab import parser

def test_key_values():
    props = {}
    content = """\
My variable: 89
other attribute name: 1234
"""
    parser.parse_key_value_patterns(content, props)
    assert {'my_variable': 89, 'other_attribute_name': 1234} == props
