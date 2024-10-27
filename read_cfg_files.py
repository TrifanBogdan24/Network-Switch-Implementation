#!/usr/bin/env python3

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
        return f"Interface name: {self.name}\n{self.port_type}"

# MyTODO
class SwitchConfig:
    def __init__(self, switch_id: int, interfaces: List[SwitchInterface]):
        self.switch_id = switch_id
        self.interfaces = interfaces


class SwitchConfig:
    def __init__(self, switch_id: int, interfaces: List[SwitchInterface]):
        self.switch_id = switch_id
        self.interfaces = interfaces

    # TODO: beatify the output string
    def __str__(self):
        interfaces_str = ",\n".join(
            f"\t{{\n\t\t\"Interface name\": \"{interface.name}\",\n\t\t\"{interface.port_type}\"\n\t}}"
            for interface in self.interfaces
        )
        return f"""\
{{
    "SwitchID": {self.switch_id},
    "Interfaces": [
        {interfaces_str}
    ]
}}"""

# MyTODO
def read_config_file(filepath: str) -> SwitchConfig:
    try:
        with open(filepath, 'r') as file:
            switch_id = int(file.readline().strip())
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

            return SwitchConfig(switch_id, interfaces)
    except Exception as err:
        print(f"[ERROR] Eroare la citirea fișierului {filepath}: {err}")
        return None  # Asigură-te că returnezi None în caz de eroare




def main():
    switch_0 = read_config_file("configs/switch0.cfg")
    switch_1 = read_config_file("configs/switch1.cfg")



    print(switch_0)
    print(switch_1)


if __name__ == '__main__':
    main()