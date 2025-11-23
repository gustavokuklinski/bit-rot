import xml.etree.ElementTree as ET
import os

def parse_xml_file(filepath):
    """Parses a generic XML file and returns the ElementTree object."""
    tree = ET.parse(filepath)
    return tree