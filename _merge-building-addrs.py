#!/usr/bin/env python3
# vim: fileencoding=utf-8 encoding=utf-8 et sw=4

import sys
import os
import xml.etree.ElementTree as ElementTree
import string
import argparse

def print_usage():
    print("Usage: python3 script_name.py <building_file.osm> <address_file.osm> [options]")
    print("\nThis script processes OpenStreetMap (OSM) data to combine building outlines with address information.")
    print("\nArguments:")
    print("  building_file.osm    OSM file containing building data")
    print("  address_file.osm     OSM file containing address data")
    print("\nOptions:")
    print("  -h, --help           Show this help message and exit")
    print("  -o OUTPUT, --output OUTPUT")
    print("                       Specify the output file name (default: output.osm)")

# Parse command line arguments
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('-h', '--help', action='store_true', help='Show help message and exit')
parser.add_argument('files', nargs='*', help='Input OSM files')
parser.add_argument('-o', '--output', default='output.osm', help='Specify the output file name')

args = parser.parse_args()

if args.help or len(args.files) != 2:
    print_usage()
    sys.exit(0)

building_file, address_file = args.files
output_file = args.output

outroot = ElementTree.Element("osm", {"version": "0.6"})
bldgroot = ElementTree.parse(building_file).getroot()
addrroot = ElementTree.parse(address_file).getroot()

waynodes = {}
bldgs = []
addrs = []

# Read the building outlines
for elem in bldgroot:
    if 'id' not in elem.attrib:
        continue
    id = int(elem.attrib['id'])
    if elem.tag == 'node':
        lat = float(elem.attrib['lat'])
        lon = float(elem.attrib['lon'])
        waynodes[id] = (lat, lon)
        outroot.append(elem)
    if elem.tag != 'way':
        outroot.append(elem)
        continue
    tags = {}
    for sub in elem:
        if sub.tag != 'tag':
            continue
        v = sub.attrib['v'].strip()
        if v:
            tags[sub.attrib['k']] = v

    # Tag transformations can happen here

    # Parse the geometry, store in a convenient format,
    # also find some point in the middle of the outline to be used to
    # speed up distance calculation
    way = []
    refs = []
    j = 0
    lat = 0.0
    lon = 0.0
    for sub in elem:
        if sub.tag != 'nd':
            continue
        ref = int(sub.attrib['ref'])
        if ref not in waynodes:
            print(f"Warning: Node {ref} referenced in way {id} not found", file=sys.stderr)
            continue
        way.append(waynodes[ref])
        refs.append(ref)
        j += 1
        lat += waynodes[ref][0]
        lon += waynodes[ref][1]

    if j == 0:
        print(f"Warning: Way {id} has no valid nodes", file=sys.stderr)
        outroot.append(elem)
        continue

    lat /= j
    lon /= j

    if refs[0] != refs[-1]:
        print(f"Warning: Way {id} is not closed", file=sys.stderr)
        outroot.append(elem)
        continue

    if 'version' in elem.attrib:
        v = int(elem.attrib['version'])
    else:
        v = 1
    bldgs.append((lat, lon, way, refs, tags, id, v, []))
bldgroot = None  # Make python release the XML structure

def contains(poly, pos):
    cont = False
    prev = poly[0]
    for node in poly[1:]:
        if (node[1] > pos[1]) != (prev[1] > pos[1]) and pos[0] < node[0] + \
                (prev[0] - node[0]) * (pos[1] - node[1]) / (prev[1] - node[1]):
            cont = not cont
        prev = node
    return cont

# Read the address nodes data
for elem in addrroot:
    if 'id' not in elem.attrib:
        continue
    tags = {}
    for sub in elem:
        if sub.tag != 'tag':
            continue
        v = sub.attrib['v'].strip()
        if v:
            tags[sub.attrib['k']] = v
    if elem.tag != 'node':
        continue
    lat = float(elem.attrib['lat'])
    lon = float(elem.attrib['lon'])

    id = int(elem.attrib['id'])
    if 'version' in elem.attrib:
        v = int(elem.attrib['version'])
    else:
        v = 1
    addr = (lat, lon, tags, id, v, [])
    addrs.append(addr)

    # Find what if any building shapes contain this lat/lon
    for elat, elon, way, refs, btags, id, v, newaddrs in bldgs:
        if 'addr:housenumber' in btags:
            continue
        if abs(elat - lat) + abs(elon - lon) > 0.006:
            continue
        if not contains(way, (lat, lon)):
            continue
        newaddrs.append(addr)
        break
addrroot = None

for lat, lon, way, refs, tags, id, v, newaddrs in bldgs:
    attrs = {"version": str(v), "id": str(id)}

    # If this building contains only a single address node, copy its tags
    # to the building way and mark the node as no longer needed.
    if len(newaddrs) == 1:
        newaddrs[0][5].append(1)
        if 'source' in newaddrs[0][2]:
            newaddrs[0][2]['source:addr'] = newaddrs[0][2]['source']
            del newaddrs[0][2]['source']
        tags.update(newaddrs[0][2])
        attrs['action'] = 'modify'

    elem = ElementTree.SubElement(outroot, "way", attrs)
    for k in tags:
        ElementTree.SubElement(elem, 'tag', {'k': k, 'v': tags[k]})
    for ref in refs:
        ElementTree.SubElement(elem, 'nd', {'ref': str(ref)})

# Add remaining addresses as nodes
for lat, lon, tags, id, v, bbs in addrs:
    if bbs:
        continue

    i = id
    if i < 0:
        i -= 2000000
    elem = ElementTree.SubElement(outroot, "node", {
        'lat': str(lat),
        'lon': str(lon),
        "version": str(v),
        "id": str(i)})
    for k in tags:
        ElementTree.SubElement(elem, 'tag', {'k': k, 'v': tags[k]})

print(f"Writing to {output_file}")
ElementTree.ElementTree(outroot).write(output_file, encoding="utf-8", xml_declaration=True)
