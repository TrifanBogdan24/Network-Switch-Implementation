#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name






def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    # Check for VLAN tag (0x8100 in network byte order is b'\x81\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id

def create_vlan_tag(vlan_id):
    # 0x8100 for the Ethertype for 802.1Q
    # vlan_id & 0x0FFF ensures that only the last 12 bits are used
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)

def send_bdpu_every_sec():
    while True:
        # TODO Send BDPU every second if necessary
        time.sleep(1)







# MyTODO
def send_to_link_with_VLAN_tag(src_interface, dst_interface, length, data):
    """
    Function 'wrapped' on send_to_link
    Additional logic for VLAN tag   -> Implements VLAN support
    
    
    Interfaces rr-0-[0-1]
    """
    switch_id = sys.argv[1]
    



    if switch_id == 14:
        # switch 0
        # Please see: configs/switch0.cfg
        if get_interface_name(src_interface) == "r-0" and get_interface_name(dst_interface) in ["rr-0-1", "rr-0-2"]:
            tagged_frame = data[0:12] + create_vlan_tag(1) + data[12:]
            send_to_link(dst_interface, length + 4, tagged_frame)  # The size of VLAN TAG is 4 bits
            return
        
        if get_interface_name(src_interface) == "r-1" and get_interface_name(dst_interface) in ["rr-0-1", "rr-0-2"]:
            tagged_frame = data[0:12] + create_vlan_tag(2) + data[12:]
            send_to_link(dst_interface, length + 4, tagged_frame)  # The size of VLAN TAG is 4 bits
            return
        
        if get_interface_name(src_interface) in ["rr-0-1", "rr-0-2"] and get_interface_name(src_interface) in ["rr-0-1", "rr-0-2"]:
            # Comunicatie intre doua linii trunk: se trimite pachetul asa cum se primeste
            send_to_link(dst_interface, length, data)
            return

        if get_interface_name(src_interface) in ["rr-0-1", "rr-0-2"] and get_interface_name(dst_interface) in ["r-0", "r-1"]:
            # The packet was received from a TRUNK line
            # Therefore, it was TAGGED

            vlan_tci = int.from_bytes(data[14:16], byteorder='big')
            vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID

            untagged_frame = data[0:12] + data[16:]

            if get_interface_name(src_interface) == "r-0":# Removing 4 bits (size of VLAN)
                if vlan_id == 1:
                    send_to_link(dst_interface, length - 4, untagged_frame)  # Removing 4 bits (size of VLAN)
                    return
                else:
                    # Cannot transmit a pachtet in different VLANs
                    return
            
            if get_interface_name(src_interface) == "r-1":
                if vlan_id == 2:
                    send_to_link(dst_interface, length - 4, untagged_frame)  # Removing 4 bits (size of VLAN)
                    return
                else:
                    # Cannot transmit a pachtet in different VLANs
                    return
                


    elif switch_id == 10:
        # switch 1
        # Please see: configs/switch1.cfg
        if get_interface_name(src_interface) == "r-0" and get_interface_name(dst_interface) in ["rr-0-1", "rr-0-2"]:
            tagged_frame = data[0:12] + create_vlan_tag(1) + data[12:]
            send_to_link(dst_interface, length + 4, tagged_frame)  # The size of VLAN TAG is 4 bits
            return
        
        if get_interface_name(src_interface) == "r-1" and get_interface_name(dst_interface) in ["rr-0-1", "rr-0-2"]:
            tagged_frame = data[0:12] + create_vlan_tag(1) + data[12:]
            send_to_link(dst_interface, length + 4, tagged_frame)  # The size of VLAN TAG is 4 bits
            return
        
        if get_interface_name(src_interface) == "r-0" and get_interface_name(dst_interface) == "r-1":
            # Comunicatie intre cei doi hosti din acelasi VLAN
            send_to_link(dst_interface, length, data)
            return

        if get_interface_name(src_interface) in ["rr-0-1", "rr-0-2"] and get_interface_name(src_interface) in ["rr-0-1", "rr-0-2"]:
            # Comunicatie intre doua linii trunk: se trimite pachetul asa cum se primeste
            send_to_link(dst_interface, length, data)
            return
        
        if get_interface_name(src_interface) in ["rr-0-1", "rr-0-2"] and get_interface_name(dst_interface) in ["r-0", "r-1"]:
            # The packet was received from a TRUNK line and moves in an ACCESS LINE
            # Therefore, it was TAGGED

            vlan_tci = int.from_bytes(data[14:16], byteorder='big')
            vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID

            untagged_frame = data[0:12] + data[16:]

            if get_interface_name(src_interface) == "r-0":
                if vlan_id == 1:
                    send_to_link(dst_interface, length - 4, untagged_frame)  # Removing 4 bits (size of VLAN)
                    return
                else:
                    # Cannot transmit a pachtet in different VLANs
                    return
            
            if get_interface_name(src_interface) == "r-1":
                if vlan_id == 1:
                    send_to_link(dst_interface, length - 4, untagged_frame)  # Removing 4 bits (size of VLAN)
                    return
                else:
                    # Cannot transmit a pachtet in different VLANs
                    return
            
    else:
        # Other switch, different from 0 and 1
        send_to_link(dst_interface, length, data)




def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]

    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    # myTODO: init the CAM table
    CAM_table = {port: None for port in range(num_interfaces)}

    print("# Starting switch with id {}".format(switch_id), flush=True)
    print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))

    # Create and start a new thread that deals with sending BDPU
    t = threading.Thread(target=send_bdpu_every_sec)
    t.start()

    # Printing interface names
    for i in interfaces:
        print(get_interface_name(i))

    while True:
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()

        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)

        # Print the MAC src and MAC dst in human readable format
        dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac = ':'.join(f'{b:02x}' for b in src_mac)

        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(10) + data[12:]

        print(f'Destination MAC: {dest_mac}')
        print(f'Source MAC: {src_mac}')
        print(f'EtherType: {ethertype}')

        print("Received frame of size {} on interface {}".format(length, interface), flush=True)

        # TODO: Implement forwarding with learning

        # myTODO: updatez interfata pe care a venit pachetul cu adresa MAC sursa a pachetului
        CAM_table[interface] = src_mac
        
        src_interface = interface
            
        found_dst_interface: bool = False


        # MyTODO: cuatam interfata care are mapata adresa MAC destinatie
        for dst_interface in interfaces:
            if dst_interface == interface:
                continue
            if CAM_table[dst_interface] == dest_mac:
                # myTODO: Implement VLAN support
                send_to_link_with_VLAN_tag(src_interface, dst_interface, length, data)
                found_dst_interface = True
                break

        if found_dst_interface == False:
            # MyTODO: facem broadcast: trimitem packetul pe toate interfetele, mai putin pe cea pe care a venit
            # dst_interface = interfata
            for dst_interface in interfaces:
                if dst_interface == interface:
                    continue
                # myTODO: Implement VLAN support
                send_to_link_with_VLAN_tag(src_interface, dst_interface, length, data)






        # TODO: Implement VLAN support
        # TODO: Implement STP support

        # data is of type bytes.
        # send_to_link(i, length, data)

if __name__ == "__main__":
    main()
