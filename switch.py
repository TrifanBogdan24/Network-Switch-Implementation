#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name

from typing import List, Union




# MyTODO
class Trunk:
    def __init__(self):
        self.is_trunk = True
    
    def __str__(self):
        return "Interface Type: TRUNK"

# MyTODO
class Access:
    def __init__(self, vlan_id: int):
        self.vlan_id = vlan_id

    def __str__(self):
        return f"Interface Type: ACCESS (vlan_id={self.vlan_id})"

# MyTODO
class SwitchInterface:
    def __init__(self, name: str, port_type: Union[Trunk, Access]):
        self.name = name
        self.port_type = port_type

    def __str__(self):
        """
        Returns a JSON formatted string
        """
        string = ""
        string += "{\n"
        string += f"\t\"Interface name\": {self.name},\n"

        # Kind a pattern matching
        if isinstance(self.port_type, Trunk):
            string += f"\t\"Interface type\": TRUNK\n"
        elif isinstance(self.port_type, Access):
            string += f"\t\"Interface type\": ACCESS (vlan_id={self.port_type.vlan_id})\n"

        string += "}"
        return string

# MyTODO
class SwitchConfig:
    def __init__(self, switch_id: int, switch_priority: int, interfaces: List[SwitchInterface]):
        self.switch_id = switch_id
        self.switch_priority = switch_priority
        self.interfaces = interfaces

    def __str__(self):
        """
        Returns a JSON formatted string
        """
        string = ""
        string += "{\n"
        string += f"\t\"SwitchID\": {self.switch_id},\n"
        string += f"\t\"Switch Priority\": {self.switch_priority},\n"

        if len(self.interfaces) == 0:
            string += "\t\"Switch Interfaces\": []\n"
            return string

        string += "\t\"Switch Interfaces\":\n"
        string += "\t[\n"

        iter = 0
        for interface in self.interfaces:
            string += "\t\t{\n"
            string += f"\t\t\t\"Interface name\": {interface.name},\n"

            # Kind a pattern matching
            if isinstance(interface.port_type, Trunk):
                string += f"\t\t\t\"Interface type\": TRUNK\n"
            elif isinstance(interface.port_type, Access):
                string += f"\t\t\t\"Interface type\": ACCESS (vlan_id={interface.port_type.vlan_id})\n"


            
            iter = iter + 1
            if iter == len(self.interfaces):
                string += "\t\t}\n"
            else:
                string += "\t\t},\n"
        string += "\t]\n"
        string += "}"
        return string
    
    def getInterfaceByName(self, name: str) -> Union[Trunk, Access]:
        for interface in self.interfaces:
            if interface.name == name:
                return interface.port_type
        return None

# MyTODO
def read_config_file(switch_id: int, filepath: str) -> SwitchConfig:
    try:
        with open(filepath, 'r') as file:
            switch_priority = int(file.readline().strip())
            interfaces = []

            for line in file:
                line_parts = line.strip().split()
                name = line_parts[0]

                if line_parts[1] == 'T':
                    port = Trunk()
                else:
                    vlan_id: int = int(line_parts[1])
                    port = Access(vlan_id)

                interfaces.append(SwitchInterface(name, port))

            return SwitchConfig(switch_id, switch_priority, interfaces)
    except Exception as err:
        print(f"[ERROR] Eroare la citirea fișierului {filepath}: {err}")
        return None  





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
def enable_VLAN_sending(network_switch: SwitchConfig, vlan_id_packet, src_interface, dst_interface, length, data) -> None:
    """
    Function 'wrapped' on send_to_link
    Additional logic for VLAN tag   -> Implements VLAN support
    """


    if network_switch is None:
        # Switch is not in the list of switches
        send_to_link(dst_interface, length, data)
        print("Switch is None")
        return
    
    print(src_interface)
    print(dst_interface)


    src_name: str = get_interface_name(src_interface)
    dst_name: str = get_interface_name(dst_interface)

    src_port_type: Union[Trunk, Access] = network_switch.getInterfaceByName(src_name)
    dst_port_type: Union[Trunk, Access] = network_switch.getInterfaceByName(dst_name)

    if isinstance(src_port_type, Access) and isinstance(dst_port_type, Access):
        if src_port_type.vlan_id != dst_port_type.vlan_id:
            # Nu trimitem intre VLAN-uri diferite
            return
        send_to_link(dst_interface, length, data)
        return
    if isinstance(src_port_type, Trunk) and isinstance(dst_port_type, Trunk):
        send_to_link(dst_interface, length, data)
        return
    if isinstance(src_port_type, Access) and isinstance(dst_port_type, Trunk):
        new_data = data[0:12] + create_vlan_tag(int(src_port_type.vlan_id)) + data[12:]
        new_length = length + 4       # The size of VLAN TAG is 4 bits
        send_to_link(dst_interface, new_length, new_data)
        return
    if isinstance(src_port_type, Trunk) and isinstance(dst_port_type, Access):
        if int(dst_port_type.vlan_id) != int(vlan_id_packet):
            # Nu facem transmisia intre doua VLAN-uri diferite
            return
        new_data = data[0:12] + data[16:]
        new_length = length - 4       # Removing 4 bits (size of VLAN)
        send_to_link(dst_interface, new_length, new_data)
        return
    
    
    send_to_link(dst_interface, length, data)
    return
    






def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]

    # MyTODO cast to int
    switch_id: int = int(switch_id)


    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    # MyTODO init the CAM table
    CAM_table = {port: None for port in range(num_interfaces)}


    
    network_switch: SwitchConfig = read_config_file(switch_id, f"configs/switch{switch_id}.cfg")




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

        # MyTODO updatez interfata pe care a venit pachetul cu adresa MAC sursa a pachetului
        CAM_table[interface] = src_mac
        
        src_interface = interface
            
        found_dst_interface: bool = False


        # MyTODO cuatam interfata care are mapata adresa MAC destinatie
        for dst_interface in interfaces:
            if dst_interface == interface:
                # Nu trimitem pe unde a venit
                continue
            if CAM_table[dst_interface] == dest_mac:
                # MyTODO Implement VLAN support
                found_dst_interface = True
                enable_VLAN_sending(network_switch, vlan_id, src_interface, dst_interface, length, data)
                # send_to_link(dst_interface, length, data)

                break

        # MyTODO facem broadcast: trimitem packetul pe toate interfetele, mai putin pe cea pe care a venit            
        if found_dst_interface == False:
            for dst_interface in interfaces:
                if dst_interface == interface:
                    # Nu trimitem pe unde a venit
                    continue
                # MyTODO Implement VLAN support
                enable_VLAN_sending(network_switch, vlan_id, src_interface, dst_interface, length, data)
                # send_to_link(dst_interface, length, data)





        # TODO: Implement VLAN support
        # TODO: Implement STP support

        # data is of type bytes.
        # send_to_link(i, length, data)

if __name__ == "__main__":
    main()
