#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name

from typing import List, Dict, Union


# MyTODO
class Trunk:
    def __init__(self):
        self.isTrunk: bool = True
    
    def __str__(self):
        return "Port Type: TRUNK"

# MyTODO
class Access:
    def __init__(self, vlan_id: int):
        self.vlan_id: int = vlan_id

    def __str__(self):
        return f"Port Type: ACCESS (vlan_id={self.vlan_id})"




class Blocking:
    def __init__(self):
        self.isBlocked: bool = True


class Listening:
    def __init__(self):
        self.isListening: bool = True



class SwitchPort:
    def __init__(self, vlan_type: Union[Trunk, Access]):
        self.vlan_type = vlan_type
        self.stp_type: Union[Blocking, Listening] = Listening()
        self.is_designated_port: bool = True


# MyTODO
class SwitchConfig:
    _instance = None

    def __new__(cls, switch_id: int = None, switch_priority: int = None, interfaces: Dict[str, SwitchPort] = None):
        """
        Configuratia switch-ului este unica
        Clasa poate fi Singleton :)))
        """
        if cls._instance is None:
            cls._instance = super(SwitchConfig, cls).__new__(cls)
            cls._instance.switch_id = switch_id
            cls._instance.switch_priority = switch_priority
            cls._instance.interfaces = interfaces or {}

            # Variables for STP (set to default when creating switch)
            cls._instance.own_bridge_id = switch_priority
            cls._instance.root_bridge_id = cls._instance.own_bridge_id
            cls._instance.root_path_cost = 0
            cls._instance.root_port = None
        return cls._instance

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

        # Iterating all KEYS (interface names) and VALUES (interface values "T"/number)
        for interface_name, interface_type in self.interfaces.items():
            string += "\t\t{\n"
            string += f"\t\t\t\"Interface name\": {interface_name},\n"



            iter = iter + 1
            if iter == len(self.interfaces):
                string += "\t\t}\n"
            else:
                string += "\t\t},\n"
        string += "\t]\n"
        string += "}"
        return string
    
    def getInterfaceByName(self, name: str) -> SwitchPort:
        if name in self.interfaces:
            return self.interfaces[name]
        # The KEY (interface name) is not in dictionary
        return None

# MyTODO
def read_config_file(switch_id: int, filepath: str) -> SwitchConfig:
    try:
        with open(filepath, 'r') as file:
            switch_priority = int(file.readline().strip())
            interfaces = {}

            for line in file:
                line_parts = line.strip().split()
                name = line_parts[0]


                if line_parts[1] == "T":
                    interfaces[name] = SwitchPort(Trunk())
                else:
                    vlan_id = int(line_parts[1])
                    interfaces[name] = SwitchPort(Access(vlan_id))
            
            return SwitchConfig(switch_id, switch_priority, interfaces)
    except Exception as err:
        print(f"[ERROR] Eroare la citirea fisierului {filepath}: {err}")
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
def is_unicast(mac):
    """
    Adresele MAC sunt compuse din 48 de biti

    O adresa MAC este considerata UNICAST
    daca primul bit din primul octet este setat la 0
    """
    return (mac[0] & 1) == 0

# MyTODO
def enable_VLAN_sending(vlan_id_packet, src_interface, dst_interface, length, data) -> None:
    """
    Function 'wrapped' on send_to_link
    Additional logic for VLAN tag   -> Implements VLAN support
    """

    network_switch = SwitchConfig()

    if network_switch is None:
        # Switch is not in the list of switches
        send_to_link(dst_interface, length, data)
        return
    


    src_name: str = get_interface_name(src_interface)
    dst_name: str = get_interface_name(dst_interface)

    src_port_type: Union[Trunk, Access] = network_switch.getInterfaceByName(src_name).vlan_type
    dst_port_type: Union[Trunk, Access] = network_switch.getInterfaceByName(dst_name).vlan_type


    if isinstance(src_port_type, Access) and isinstance(dst_port_type, Access):
        # Access -> Trunk
        if src_port_type.vlan_id != dst_port_type.vlan_id:
            # Nu trimitem intre VLAN-uri diferite
            return
        send_to_link(dst_interface, length, data)
        return
    if isinstance(src_port_type, Trunk) and isinstance(dst_port_type, Trunk):
        # Trunk -> Trunk
        send_to_link(dst_interface, length, data)
        return
    if isinstance(src_port_type, Access) and isinstance(dst_port_type, Trunk):
        # Access -> Trunk
        new_data = data[0:12] + create_vlan_tag(src_port_type.vlan_id) + data[12:]
        new_length = length + 4       # The size of VLAN TAG is 4 bits
        send_to_link(dst_interface, new_length, new_data)
        return
    if isinstance(src_port_type, Trunk) and isinstance(dst_port_type, Access):
        # Trunk -> Access
        if dst_port_type.vlan_id != int(vlan_id_packet):
            # Nu facem transmisia intre doua VLAN-uri diferite
            return
        new_data = data[0:12] + data[16:]
        new_length = length - 4       # Removing 4 bits (size of VLAN)
        send_to_link(dst_interface, new_length, new_data)
        return
    
    
    send_to_link(dst_interface, length, data)
    return
    



# MyTODO
def initialize_STP() -> None:
    network_switch = SwitchConfig()


    all_ports: List[SwitchPort] = list(network_switch.interfaces.values())
    trunk_ports: List[SwitchPort] = [port for port in all_ports if isinstance(port.vlan_type, Trunk)]

    for port in trunk_ports:
        port.stp_type = Blocking


    network_switch.own_bridge_id = network_switch.switch_priority
    network_switch.root_bridge_id = network_switch.own_bridge_id
    network_switch.root_path_cost = 0

    if network_switch.own_bridge_id == network_switch.root_bridge_id:
        pass




def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]

    # MyTODO cast to int
    switch_id: int = int(switch_id)


    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    # MyTODO init the CAM table
    CAM_table_dict = dict()     # Empty dictionary
    
    network_switch: SwitchConfig = read_config_file(switch_id, f"configs/switch{switch_id}.cfg")


    # Create and start a new thread that deals with sending BDPU
    t = threading.Thread(target=send_bdpu_every_sec)
    t.start()


    while True:
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()

        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)


        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(10) + data[12:]


        # TODO: Implement forwarding with learning

        # MyTODO updatez interfata pe care a venit pachetul cu adresa MAC sursa a pachetului
        CAM_table_dict[src_mac] = interface
        
        src_interface = interface
            

        print(dest_mac)

        # MyTODO trimiterea cadrului
        if is_unicast(dest_mac):
            # MyTODO Unicast

            if dest_mac in CAM_table_dict:
                dst_interface = CAM_table_dict[dest_mac]

                if dst_interface == src_interface:
                    continue
                enable_VLAN_sending(vlan_id, src_interface, dst_interface, length, data)

            else:
                # MyTODO Broadcast
                for dst_interface in interfaces:
                    if dst_interface == src_interface:
                        continue
                    enable_VLAN_sending(vlan_id, src_interface, dst_interface, length, data)
        else:
            # MyTODO Broadcast
            for dst_interface in interfaces:
                if dst_interface == src_interface:
                    continue
                enable_VLAN_sending(vlan_id, src_interface, dst_interface, length, data)





        # TODO: Implement VLAN support
        # TODO: Implement STP support

        # data is of type bytes.
        # send_to_link(i, length, data)

if __name__ == "__main__":
    main()
