#!/usr/bin/env python3
"""
ODR SPI Logos Generator - Gets logos from a local directory
No need for an external webserver or RadioDNS service

Based on "odr-radiodns-bridge" - Copyright (c) Nick Piggott (originally LGPL 2.1)
Modified for offline manual logos injection from a local directory.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

# ============================================================================ START OF THE USER CONFIGURATION SECTION ============================================================================

CONF_MUX_FILE = "/home/odr/ODR-mmbTools/config/odr-dabmux.info" # Indicate the path to your "odr-dabmux" file here
CONF_LOGOS_DIR = "/home/odr/ODR-mmbTools/config/mot/SPI" # Indicate the path to your logos directory here       
CONF_OUTPUT_FILE = "/home/odr/ODR-mmbTools/config/mot/spi-output.dat" # Indicate where the output file should be saved - this path will have to be indicated in your odr-dabmux configuration later
CONF_PACKET_SIZE = 48 # Must be a multiple of 3 based on the bitrate specified in the odr-dabmux configuration. Example: 48 for 16 kbps.                       
CONF_PACKET_ADDRESS = 1 # Leave the default value, unless you specifically want to use a different address. "1" for this value = "0x01" as address value in the odr-dabmux configuration file.
CONF_DATAGROUP = False # Works perfectly with "False" based on tests, only change this value if you really want to.

# ===================================== END OF THE USER CONFIGURATION SECTION - DO NOT MODIFY VALUES BELOW THIS POINT (unless you know what you are doing) ========================================

import argparse
import os, re
from datetime import datetime
import logging

from spi import Service, DabBearer, ServiceInfo, Multimedia, ShortName, MediumName, binary
from mot import MotObject, ContentType
from mot.epg import EpgContentType, ScopeId, UniqueBodyVersion
from msc.datagroups import encode_directorymode
from msc.packets import encode_packets

SIZES_MAPPING = {
    "32x32": Multimedia.LOGO_COLOUR_SQUARE,
    "112x32": Multimedia.LOGO_COLOUR_RECTANGLE,
    "128x128": Multimedia.LOGO_UNRESTRICTED,
    "320x240": Multimedia.LOGO_UNRESTRICTED
}

EXT_MAPPING = {
    ".png": ("image/png", ContentType.IMAGE_PNG),
    ".jpg": ("image/jpeg", ContentType.IMAGE_JFIF),
    ".jpeg": ("image/jpeg", ContentType.IMAGE_JFIF)
}

def find_file_case_insensitive(local_dir, sid_hex, dim):
    target_names = {}
    for ext, (mime_type, mot_type) in EXT_MAPPING.items():
        target_name_lower = f"{sid_hex}-{dim}{ext}".lower()
        target_names[target_name_lower] = (mime_type, mot_type)
        
    try:
        files_in_dir = os.listdir(local_dir)
    except Exception:
        return None, None, None

    for actual_filename in files_in_dir:
        if actual_filename.lower() in target_names:
            mime_type, mot_type = target_names[actual_filename.lower()]
            return os.path.join(local_dir, actual_filename), mime_type, mot_type
            
    return None, None, None

class Generator:
    def __init__(self, output, packet_size, packet_address, datagroup_output, ecc, eid, label, shortlabel):
        self.output = output
        self.packet_size = packet_size
        self.packet_address = packet_address
        self.datagroup_output = datagroup_output
        self.ecc = ecc
        self.eid = eid
        self.label = label
        self.shortlabel = shortlabel

    def generate_epg(self, services_config, local_dir):
        objects = []
        all_services = []
        nowutc32 = int(datetime.today().timestamp()) & 0x7FFFFFFF

        print(f"\nScanned logo folder: {local_dir}")
        print(f"Services found in the odr-dabmux file: {len(services_config)}\n")

        for s in services_config:
            bearer = s.get("bearer")
            if not bearer: continue
            sid = bearer.sid
            if sid == 0 or sid > 0xFFFF: continue

            sid_hex = f"{sid:x}".lower()
            station_label = s.get("label", f"Station_{sid_hex}")
            
            # Extract the radio-specific block to isolate its ECC and short label
            srv_match = re.search(r'id\s+(?:0x)?' + sid_hex + r'\b[^}]+', open(CONF_MUX_FILE).read(), re.IGNORECASE)
            srv_blk = srv_match.group(0) if srv_match else ""
            ecc_match = re.search(r'ecc\s+(?:0x)?([0-9a-fA-F]+)', srv_blk, re.IGNORECASE)
            short_match = re.search(r'shortlabel\s+"([^"]+)"', srv_blk, re.IGNORECASE)

            station_ecc = int(ecc_match.group(1), 16) if ecc_match else self.ecc
            station_short = short_match.group(1) if short_match else station_label[:8]
            
            svc = Service()
            svc.ecc = station_ecc
            svc.names = [MediumName(station_label[:16]), ShortName(station_short)]
            svc.bearers = [bearer]
            svc.media = []

            for dim, logo_type in SIZES_MAPPING.items():
                width, height = map(int, dim.split('x'))
                local_path, mime_type, mot_type = find_file_case_insensitive(local_dir, sid_hex, dim)
                if local_path:
                    try:
                        with open(local_path, 'rb') as f:
                            img_data = f.read()
                        objectname = f'{len(objects)+1:x}'
                        o = MotObject(objectname, img_data, mot_type)
                        o.add_parameter(UniqueBodyVersion(nowutc32))
                        objects.append(o)
                        m = Multimedia(url=objectname, type=logo_type, width=width, height=height, content=mime_type)
                        svc.media.append(m)
                    except Exception as e:
                        print(f"Error reading station logo: {e}")

            # Add all stations to the XML, even those without a logo.
            all_services.append(svc)

        # ================= SEARCH FOR THE MULTIPLEX'S LOGOS =================
        ensemble_media = []
        eid_hex = f"{self.eid:x}".lower()
        print(f"Multiplex: {self.label} | EID: '{eid_hex}' -> Looking for {eid_hex}-*.(png|jpg|jpeg)")
        
        for dim, logo_type in SIZES_MAPPING.items():
            width, height = map(int, dim.split('x'))
            local_path, mime_type, mot_type = find_file_case_insensitive(local_dir, eid_hex, dim)
            if local_path:
                print(f"Logo found for the multiplex ({dim}): {os.path.basename(local_path)}")
                try:
                    with open(local_path, 'rb') as f:
                        img_data = f.read()
                    objectname = f'{len(objects)+1:x}'
                    o = MotObject(objectname, img_data, mot_type)
                    o.add_parameter(UniqueBodyVersion(nowutc32))
                    objects.append(o)
                    m = Multimedia(url=objectname, type=logo_type, width=width, height=height, content=mime_type)
                    ensemble_media.append(m)
                except Exception as e:
                    print(f"Error while reading the multiplex's logo: {e}")
        # =====================================================================
                 
        def tlv(tag, data):
            if len(data) < 0xFE: return bytes([tag, len(data)]) + data
            else: return bytes([tag, 0xFE, (len(data) >> 8) & 0xFF, len(data) & 0xFF]) + data

        def attr_str(tag, s):
            b = s.encode('utf-8')
            return bytes([tag, len(b)]) + b

        def attr_u16(tag, val):
            return bytes([tag, 2, (val >> 8) & 0xFF, val & 0xFF])

        ens_payload = bytearray()
        ens_payload += bytes([0x80, 3, self.ecc, (self.eid >> 8) & 0xFF, self.eid & 0xFF])
        if self.shortlabel: ens_payload += tlv(0x10, tlv(0x01, self.shortlabel[:8].encode('utf-8')))
        if self.label: ens_payload += tlv(0x11, tlv(0x01, self.label[:16].encode('utf-8')))

        # Add the multiplex logos
        for m in ensemble_media:
            m_payload = bytearray()
            m_payload += attr_str(0x82, str(m.url))
            m_type = 0x04 if (m.width == 32 and m.height == 32) else 0x02
            m_payload += bytes([0x83, 1, m_type])
            m_payload += attr_u16(0x84, m.width)
            m_payload += attr_u16(0x85, m.height)
            m_payload += attr_str(0x80, m.content)
            ens_payload += tlv(0x13, tlv(0x2B, bytes(m_payload)))

        # Services
        for svc in all_services:
            b = svc.bearers[0]
            s_payload = bytearray()
            
            s_short = ""
            s_med = ""
            for n in svc.names:
                if isinstance(n, ShortName): s_short = n.text
                elif isinstance(n, MediumName): s_med = n.text
                
            if s_short: s_payload += tlv(0x10, tlv(0x01, s_short.encode('utf-8')))
            if s_med: s_payload += tlv(0x11, tlv(0x01, s_med.encode('utf-8')))

            svc_ecc = getattr(svc, 'ecc', self.ecc)
            
            # Bearer
            bearer_data = bytes([0x40, svc_ecc, (self.eid >> 8) & 0xFF, self.eid & 0xFF, (b.sid >> 8) & 0xFF, b.sid & 0xFF])
            s_payload += tlv(0x2D, tlv(0x80, bearer_data))

            for m in svc.media:
                m_payload = bytearray()
                m_payload += attr_str(0x82, str(m.url)) # url
                m_type = 0x04 if (m.width == 32 and m.height == 32) else 0x02
                m_payload += bytes([0x83, 1, m_type])   # type
                m_payload += attr_u16(0x84, m.width)    # width
                m_payload += attr_u16(0x85, m.height)   # height
                m_payload += attr_str(0x80, m.content)  # mimeValue
                s_payload += tlv(0x13, tlv(0x2B, bytes(m_payload)))

            ens_payload += tlv(0x28, bytes(s_payload))

        root_payload = bytearray()
        root_payload += attr_u16(0x80, 1)
        root_payload += attr_str(0x82, "ODR")
        root_payload += tlv(0x26, bytes(ens_payload))
        
        # 0x03 tag to create the XML file
        binary_data = tlv(0x03, bytes(root_payload))

        objectname = f'{0:x}'
        o = MotObject(objectname, binary_data, EpgContentType.SERVICE_INFORMATION)
        o.add_parameter(UniqueBodyVersion(nowutc32))
        o.add_parameter(ScopeId(self.ecc, self.eid))
        objects.insert(0, o)

        datagroups = encode_directorymode(objects, directory_parameters=[])
        
        out_dir = os.path.dirname(self.output)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        if self.datagroup_output:
            with open(self.output, 'wb') as w:
                for datagroup in datagroups:
                    w.write(datagroup.tobytes())
        else:
            packets = encode_packets(datagroups, address=self.packet_address, size=self.packet_size, padding=True)
            with open(self.output, 'wb') as w:
                for packet in packets:
                   w.write(packet.tobytes())

        try:
            os.chmod(self.output, 0o666)
        except Exception:
            pass

parser = argparse.ArgumentParser()
parser.add_argument('-f', dest='muxfile', default=CONF_MUX_FILE)
parser.add_argument('-o', dest='output', default=CONF_OUTPUT_FILE)
parser.add_argument('-L', dest='local_dir', default=CONF_LOGOS_DIR)
parser.add_argument('-p', dest='packet_size', type=int, default=CONF_PACKET_SIZE)
parser.add_argument('-a', dest='packet_address', type=int, default=CONF_PACKET_ADDRESS)
parser.add_argument('-D', dest='datagroup_output', action='store_true', default=CONF_DATAGROUP)
parser.add_argument('-X', dest='debug', action='store_true')
args = parser.parse_args()

from odr.radiodns.resolver import parse_mux_config, parse_mux_ensemble
ecc, eid, label, shortlabel = parse_mux_ensemble(args.muxfile)
services_config = parse_mux_config(args.muxfile)

generator = Generator(output=args.output, packet_size=args.packet_size, packet_address=args.packet_address, 
  datagroup_output=args.datagroup_output, ecc=ecc, eid=eid, label=label, shortlabel=shortlabel)

generator.generate_epg(services_config, args.local_dir)
