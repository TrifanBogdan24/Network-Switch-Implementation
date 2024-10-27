Cerintele rezolvate: 1


## Links

Enuntul temei: <https://ocw.cs.pub.ro/courses/rl/teme/tema1_sw>

Schelet + infrastructura de testare: <https://gitlab.cs.pub.ro/rl/tema1-public>


## Running

```bash
sudo python3 checker/topo.py
```

This will open 9 terminals, 6 hosts and 3 for the switches. On the switch terminal you will run 

```bash
make run_switch SWITCH_ID=X # X is 0,1 or 2
```

The hosts have the following IP addresses.
```
host0 192.168.1.1
host1 192.168.1.2
host2 192.168.1.3
host3 192.168.1.4
host4 192.168.1.5
host5 192.168.1.6
```

We will be testing using the ICMP. For example, from host0 we will run:

```
ping 192.168.1.2
```

Note: We will use wireshark for debugging. From any terminal you can run `wireshark&`.




## Rezolvare

### Procesul de comutare | Tabela `CAM`
---


In bucla infinita `while True` din `main`, ma folosesc de trei variabile:

- `interface` -> interfata (portul, cablul fizic) pe care pachetul a veni
- `src_mac` -> adresa MAC sursa a pachetului
- `dest_mac` -> adresa MAC destinatie a pachetului


Tabela `CAM` (Content-addressable memory) retine `asocieri` (`mapari`)
intre `interfete` si `adresa MAC`.

O `interfata` poate avea asociata la un moment de timp,
o `adresa MAC` sau niciuna.


Retin aceste interfete intr-un **dictionar Python**,
pentru care **cheile** represinta `interfete`,
iar **valorile** = `adrese MAC`.

Fiecare **cheie** (`interfata`) de la 0 la `num_interfaces`,
nu va referi initial la nicio `adresa MAC`.


```python 3
CAM_table = {i: None for i in range(num_interfaces)}
```


Atunci cand primim un pachet se updateaza `Tabela CAM`,
stiind ca `interfata` pe care a venit refera `adresa MAC sursa` a pachetului.



```python 3
CAM_table[interface] = src_mac
```


Pentru a trimite pachetul mai departe, `switch`-ul trebuie sa afle pe ce interfata sa il trimita.
Astfel, va itera peste toate `interfetele` (mai putin cea pe care a venit).
Daca vreo `interfata` refera catre `adresa MAC destinatie` a pachetului,
inseamna ca am gasit `interfata` pe care sa fie trimis pachetul,
si ii dam `send` (de fapt `send_to_link`) pe interfata respectiva.


```python 3
for dst_interface in interfaces:
    if dst_interface == interface:
        continue
    if CAM_table[dst_interface] == dest_mac:
        send_to_link(dst_interface, length, data)
        found_dst_interface = True
        break
```


Daca in schimb, nu am gasit nicio `interfata` care sa asocieze `adresa MAC destinate`,
```python 3
if found_dst_interface == False
```
atunci inseamna ca nu stim pe unde sa trimitem pachetul,
si deci il trimitem pe toate interfetele, mai putin cea pe care a venit (logic).


```python 3
# Broadcast
if found_dst_interface == False:
    for dst_interface in interfaces:
        if dst_interface == interface:
            continue
        send_to_link(dst_interface, length, data)
```





### `VLAN` (Virtual LAN)

`VLAN`-ul este construit deasupra algoritmului `tabelei CAM`.

Spunem despre interfata pe care pachetul a venit ca este `src_interface` (interfata sursa).


Spunem despre interfata/interfetele pe care ajunge pachetul sa fie trimis mai departa ca este/sunt `dst_interface` (interfata destinatie).


Cum in enunt se spune clar ca doar primele doua switch-uri vor fi pornite
(`switch0` si `switch1`), eu am hardcodat relatiile dintre interfetele celor doua,
in functie de fisierele de configuratie `configs/switch0.cfg` so `configs/switch1.cfg`.




#### `VLAN` | Switch0

Hai sa ne uitam cum arata fluxul unui pachet
de pe o `interfata` pe alta a `switch`-ului 0.


```bash
$ configs/switch0.cfg
14
r-0 1
r-1 2
rr-0-1 T
rr-0-2 T
```


| `src_interface`   | `dst_interface`    | Descriere |
| :---              | :---               | :---      |
| r-0               | rr-0-1 sau rr-0-2  | Adaugam pachetului **VLAN tag**, cu `VLAN_ID=1` |
| r-1               | rr-0-1 sau rr-0-2  | Adaugam pachetului **VLAN tag**, cu `VLAN_ID=2` |
| rr-0-1 sau rr-0-2 | r-0                | Trimitem pachetul catre r-0 daca si numai daca `VLAN_ID == 1`. La trimitere, stergem **VLAN tag**-ul pachetului |
| rr-0-1 sau rr-0-2 | r-1                | Trimitem pachetul catre r-0 daca si numai daca `VLAN_ID == 2`. La trimitere, stergem **VLAN tag**-ul pachetului |
| rr-0-1 sau rr-0-2 | rr-0-2 sau rr-0-1  | Trimitem pachetul mai departe, asa cum l-am preluat |

> Nu putem trimite un pachet pe interfata pe care a venit,
> cu alte cuvinte `src_interface != dst_interface`.

Tabelul de mai sus se traduce in urmatorul cod:


```python
src_name: str = get_interface_name(src_interface)
dst_name: str = get_interface_name(dst_interface)

if switch_id == 14:
    if src_name == "r-0" and dst_name in ["rr-0-1", "rr-0-2"]:
        # Adauga VLAN tag = 1 si trimite pachetul
        send_to_link(dst_interface, more_length, more_data)
        return
    if src_name == "r-1" and dst_name in ["rr-0-1", "rr-0-2"]:
        # Adauga VLAN tag = 2 si trimite pachetul
        send_to_link(dst_interface, more_length, more_data)
        return
    if src_name in ["rr-0-1", "rr-0-2"] and dst_name == "r-0":
        if get_vlan_id() == 1:
            # Sterge VLAN tag-ul si trimite pachetul
            send_to_link(dst_interface, less_length, less_data)
            return
        return
    if src_name in ["rr-0-1", "rr-0-2"] and dst_name == "r-1":
        if get_vlan_id() == 2:
            # Sterge VLAN tag-ul si trimite pachetul
            send_to_link(dst_interface, less_length, less_data)
            return
        return
    if src_name in ["rr-0-1", "rr-0-2"] and dst_name in ["rr-0-1", "rr-0-2"]:
        # Trimite pachetul asa cum l-ai primit
        send_to_link(dst_interface, length, data)
        return
    return
```


#### `VLAN` | Switch1


Logica de implementare este similare pentru `switch`-ul 1.

```sh
$ cat configs/switch1.cfg 
10
r-0 1
r-1 1
rr-0-1 T
rr-1-2 T
```



| `src_interface`   | `dst_interface`   | Descriere |
| :---              | :---              | :---      |
| r-0  sau r1       | rr-0-1 sau rr-1-2 | Adaugam pachetului **VLAN tag**, cu `VLAN_ID=1` |
| rr-0-1 sau rr-1-2 | r-0 sau r-1       | Trimitem pachetul catre r-0 daca si numai daca `VLAN_ID == 1`. La trimitere, stergem **VLAN tag**-ul pachetului |
| r-0 sau r-1       | r-1 sau r-0       | Trimitem pachetul asa cum a fost primit (ele fac parte din acelasi VLAN, cu VLAN_ID=1) | 
| rr-0-1 sau rr-0-2 | rr-0-2 sau rr-0-1 | Trimitem pachetul mai departe, asa cum l-am preluat |


Implementarea logicii ar fi:

```python
src_name: str = get_interface_name(src_interface)
dst_name: str = get_interface_name(dst_interface)

if switch_id == 10:
    if src_name in ["r-0", "r-1"] and dst_name in ["rr-0-1", "rr-0-2"]:
        # Adaugam VLAN tag = 1 si trimite pachetul
        send_to_link(dst_interface, more_length, more_data)
        return
    if src_name in ["rr-0-1", "rr-0-2"] and dst_name in ["r-0-1", "r-0-2"]:
        if get_vlan_id(data) == 1:
            # Stergem VLAN tag-ul si trimite pachetul
            send_to_link(dst_interface, less_length, less_data)
            return
        return
    if src_name == ["r-0", "r-1"] and dst_name == ["r-0", "r-1"]:
        # Interfetele sursa si destinatie vor fi diferite
        # Trimitem pachetul asa cum l-am primit (suntem in VLAN 1)
        send_to_link(dst_interface, length, data)
        return
    if src_name == ["rr-0-1", "rr-0-2"] and dst_name == ["rr-0-1", "rr-0-2"]:
        # Interfetele sursa si destinatie vor fi diferite
        # Trimitem pachetul asa cum l-am primit
        send_to_link(dst_interface, length, data)
        return
    return
```



#### `VLAN` | Alte Switch-uri


```python
if switch_id != 14 and switch_id != 10:
    # Other switch, different than 0 and 1
    send_to_link(dst_interface, length, data)
    return
```



#### Functii helper


```python
def get_vlan_id(data):
    vlan_tci = int.from_bytes(data[14:16], byteorder='big')
    vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
    return vlan_id
```


```python
def send_tagged_frame_to_link(vlan_id, dst_interface, length, data):
    tagged_frame = data[0:12] + create_vlan_tag(1) + data[12:]
    send_to_link(dst_interface, length + 4, tagged_frame)  # The size of VLAN TAG is 4 bits
```


```python
def send_untagged_frame_to_link(dst_interface, length, data):
    untagged_frame = data[0:12] + data[16:]
    send_to_link(dst_interface, length - 4, untagged_frame)  # Removing 4 bits (size of VLAN)
```