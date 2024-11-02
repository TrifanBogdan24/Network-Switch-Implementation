Cerintele rezolvate: 1, 2, 3


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


In bucla infinita `while True` din `main()`, ma folosesc de trei variabile:

- `interface` -> interfata (portul, cablul fizic) pe care pachetul a veni
- `src_mac` -> adresa MAC sursa a pachetului
- `dest_mac` -> adresa MAC destinatie a pachetului


In cazul in `adresa MAC sursa` este nu este adresa de **unicast**,
fac **broadcast**, trimitand pachetul pe toate porturile, mai putin pe cel pe care a venit,
altfel, are loc procesul de invatare, bazat pe tabela `CAM`.

> O adresa MAC este adresa de unicast daca primul bit din primul octet este setat la 0.


Tabela `CAM` (Content-addressable memory) retine `asocieri` (`mapari`)
intre `interface_id` si `adresa MAC`.

O `interfata` poate avea asociata la un moment de timp,
o `adresa MAC` sau niciuna.


Atat `interfetele`, cat si `adresele MAC` sunt unice in tabela `CAM`. 


Aceste asocieri le retin intr-un **dictionar Python**,
iar ordinea in care sunt mapate influenteaza complexitatea in timp a executiei programului.

De vreme ce cunosc `adresa MAC sursa` si `adresa MAC destinatie` a pachetului pe care il primesc,
este de inteles ca voi accesa tabela `CAM` in functie de aceste valori.

> Tabela CAM: { MAC -> id_interfata }


> Spun *id_interfata*, pentru ca un port are o structura mult mai complexa decat un identificator numeric,
> iar ID-ul este doar un camp din cadrul structurii mele ce desemneaza un port al switch-ului,
> dar asta voi explica pe parcurs.


Astfel, incep printr-un dictionar vid (la inceput nu stim nimic despre maparile dintre interfete si adresele MAC):
```python
CAM_table_dict: Dict[bytes, int] = dict()     # Dictionar vid
```


Apoi, pe parcurs ce primesc pachetele, updatez tabela CAM,
modificand valoarea cheii `adresei MAC sursa` cu interfata pe care a venit.

```python
CAM_table_dict[src_mac] = interface
```

> La primire are loc procesul de invatare.
>
> Switch-ul face asocierile efective intre `adrese MAC` si `port`-uri
> doar atunci cand primeste.


In cazul in care `adresa MAC destinatie` nu se afla in **dictionarul** tabelei CAM,
inseamna ca nu stiu pe ce port sa trimit (`adresa MAC destinatie` nu are mapata o `interfata`),
deci fac **broadcast**, trimitand pe toate port-urile, mai putin cel pe care a venit.

Daca in schimb `adresa MAC destinatie` se gaseste in **dictionar**,
atunci spun despre ea ca geseste in tabela CAM a switch-ului.
Drep pentru care stiu exact pe ce port sa trimit (fac **unicast**):
pe portul mapat in dictionar la `adresa MAC destinatie`.


> La trimitere switch-ul nu invata nimic.
>
> Doar se foloseste de tabela CAM (informatiile pe care le stie deja)
> pentru a decide unde sa trimita.






### `VLAN` (Virtual LAN)
---


`VLAN`-ul este construit peste algoritmul `tabelei CAM`.

Spunem despre interfata pe care pachetul a venit pachetul este `src_interface` (interfata sursa).


Spunem despre interfata/interfetele pe care ajunge pachetul sa fie trimis mai departa ca este/sunt `dst_interface` (interfata destinatie).

Voi incepe prin a citi fisierul de configuratie al switch-ului.
Id-ul switch-ului, obtinut ca argument in linia de comanda, `switch_id = sys.argv[1]`
il voi folosi pentru a sti exact ce fisier sa citesc.

```python
switch_id = sys.argv[1]
network_switch = read_config_file(switch_id, f"configs/switch{switch_id}.cfg")
```


Fisierul de configuratie este ulterior parsat intr-o structura de date,
reprezentata de clasa `SwitchConfig`
care va contine urmatoarele informatii:
- ID-ul switch-ului
- Prioritatea switch-ului
- Interfetele switch-ului (retinute drept **asocieri** intre numele interfetei si tipul interfetei)



Am optat pentru implementarea interfetelor citite din fisierul de configuratie sub forma unei **liste**.
Pentru a retine informatiile unui port am optat pentru crearea unei clase aditionale `SwitchPort` care stocheaza:
- ID-ului port-ului (e.g. 0, 1, 2, 3)
- Numele port-ului (e.g. "r-0", "r-1", "rr-0-1", "rr-0-2")
- Tipul portului (`Trunk`/`Access`)
- Starea porturului (`Blocking`, `Root`, `Designated`): o folosim in viitor la STP
 - > Porturile `Root` si `Designated` sunt mereu in starea `Listening` 




Fisierul de configuratie al switch-ului
contine pe prima linie un numar, reprezentand `switch_id`-ul,
iar mai apoi, pe toate celelalte:
numele interfetei switch-ului (e.g. "r-1" sau "rr-0-1")
si litera "T" (insemnand ca interfata este configurata a fi o linie `trunk`)
sau un numar (insemnand o linie de `access`, avand `VLAN ID`-ul egal cu numarul respectiv).



In timpul procesului de invatare (`tabela CAM`),
in loc sa trimit direct pachetul,
apelez o functie construita peste `send_to_link`, care,
in functie de tipul porturilor sursa si destinatie (`trunk` / `access`),
trimite sau nu pachetul, cu sau fara **TAG** de VLAN.


`VLAN`-ul introduce astfel 4 cazuri:

- 1\. Portul pe care pachetul a venit este de tip `access`, iar portul destinatie este `access`:
trimit pachetul **daca si numai daca** porturile au acelasi `VLAN ID`
(altfel nu trimit nimic)

- 2\. Portul sursa este `trunk` si portul destinatie este `trunk`:
trimit pachetul asa cum a venit

- 3\. Portul sursa este `access`, iar portul destinatie este `trunk`:
adaug **TAG**-ul de `VLAN` in pachet,
avand `VLAN ID`-ul egal cu cel al interfetei sursa,
si trimit pachetul.


- 4\. Portul sursa este `trunk`, iar portul destinatie este `access`,
trimit pachetul **daca si numai daca**
`VLAN ID`-ul din pachet coincide cu `VLAN ID`-ului portului destinatie,
caz in care elimin **TAG**-ul de `VLAN` din pachet inainte sa trimit
(altfel, daca `VLAN ID`-urile sunt diferite, pachetul se va pierde)


Aceasta logica se implementeaza in cod, facand **pattern matching**
intre tipurile (`trunk` / `access`) porturilor sursa si destinatie.



## `STP` (Spanning Tree Protocol)
---


> Cand vorbim de un `bridge` (in cadrul STP), ne referim exclusiv la un `switch`.


Un port `trunk` poate fi, la un moment de timp, in una din urmatoarele 3 stari:
- `Blocking`
- `Root`
- `Designated`

> Spunem despre porturile `Root` si `Designated` ca sunt in starea `Listening`.


Pentru simplitate, am creat o functie, pe care o apelez o singura data
si care intoarce ca rezultat o lista cu toate porturile de tip `trunk`.


Implementarea algoritmului de `STP` se bazeaza pe celor 3 pseudocoduri din enunt,
dupa cum urmeaza.

> In textul de mai jos, ID-ul unui switch/bridge inseamna de fapt prioritatea
> (citita din prima linie a fisierului de configuratie).


### Initializare
---

La inceput, switch-ul este considerat a fi root bridge,
drept pentru care ID-ului bridge-ului radacina va coincide cu ID-ul switch-ului (adica cu prioritatea sa),
costul legaturii de la root bridge la switch este 0 (de vreme ce switch-ul este totuna cu root bridge),
iar toate port-urile trunk vor fi in starea **designated**.


### Trimiterea pachetelor BPDU la fiecare secunda
---


La fiecare secunda,
voi trimite pe toate port-urile trunk (inclusiv si pe cele `Blocking`)
pachete BPDU pentru ca celelalte switch-ul sa isi poata updata rolul (`root bridge`/`non-root bridge`), cat si starea fiecarui port (`Bloocking`/`Designated`/`Root`).

Pachetele BPDU trimise de switch vor contine urmatoarele informatii:
- ID-ului switch-ului radacina
- ID-ului switch-ului curent
- Costul de la switch-ul curent la switch-ul radacina

Switch-ul se va considera a fi **root bridge**,
drept pentru care ID-ul bridge-ului radacina coincide cu ID-ul switch-ului curent,
iar costul este egal cu 0.



Pentru constructia pachetului BPDU, respect urmatorul format:


```
 Size (bytes) 6        6       2           3            4           31
            DST_MAC|SRC_MAC|LLC_LENGTH|LLC_HEADER|BPDU_HEADER|BPDU_CONFIG
```

Pentru BPDU_CONFIG:
```
  uint8_t  flags;
  uint8_t  root_bridge_id[8];
  uint32_t root_path_cost;
  uint8_t  bridge_id[8];
  uint16_t port_id;
  uint16_t message_age;
  uint16_t max_age;
  uint16_t hello_time;
  uint16_t forward_delay;
```


### Primirea pachetelor BPDU
---

In cazul in care primesc un pachet si `adresa MAC destinatie`
nu este **unicast** (are primul bit din primul octet setat la **1**),
atunci compar `adresa MAC destinatie` cu adresa multicast **01:80:C2:00:00:00**,
transformand adresa MAC destinatie (scrisa in bytes) intr-un string human-readable
si o compar cu adresa specificata mai devreme.
Daca cele doua string-uri coincid, inseamna ca pachetul primit este de fapt un pachet BPDU,
drept pentru care trebuie sa il interpretez (pentru a updata rolul switch-ului si starile porturilor trunk)
si nu o sa mai fac broadcast.

Interpretarea unui astfel de pachet presupune, asa cum se observa si in pseudocod,
aflarea urmatoarelor valori:
- `BPDU.root_bridge_ID`
- `BPDU.sender_path_cost`
- `BPDU.sender_bridge_ID`


Dupa cum inteleg structura unui pachet BPDU,
root_bridge_id-ul ocupa 8 bytes si are offset-ul in pachet egal cu 22.

De ce 8 si 22?
- 22 = numarul de biti de la inceputul pachetului si inceputul vairabilei `BPDU.root_bridge_ID`
- 8 = dimensiunea in bytes a variabilei

La fel si pentru celelalte doua variabile

Hai sa aruncam inca o privire pe structura unui astfel de pachet:
```
 Size (bytes) 6        6       2           3            4           31
            DST_MAC|SRC_MAC|LLC_LENGTH|LLC_HEADER|BPDU_HEADER|BPDU_CONFIG

Iar BPDU Config are urmatoarea structura:
  uint8_t  flags;                  <- 1 byte
  uint8_t  root_bridge_id[8];      <- 8 bytes, offset=(6+6+2+3+4+1)=22
  uint32_t root_path_cost;         <- 4 bytes, offset=22+4=34
  uint8_t  bridge_id[8];           <- 8 bytes, offset=34+8=42
  uint16_t port_id;
  uint16_t message_age;
  uint16_t max_age;
  uint16_t hello_time;
  uint16_t forward_delay;
```


Destructurarea unui pachet BPDU se traduce astfel in cod:

```python
bpdu_root_bridge_id: int = int.from_bytes(data[22:30], byteorder='big')
bpdu_sender_path_cost: int = int.from_bytes(data[30:34], byteorder='big')
bpdu_sender_bridge_id: int = int.from_bytes(data[34:42], byteorder='big')
```



La primirea unui pachet BPDU, dupa destructurare, tot ceea ce fac
este sa implementez in cod pseudocodul din enut, cu urmatoarele mentiuni:
- Pentru a nu complica lucrurile: porturile `Designated` si `Root` sunt considerate a fi si `Listening` (deci nu trebuie sa tratez un caz separat pentru port-urile `Listening`)
- Pastrez intr-o variabila **booleana** (`network_switch.is_root_bridge`)
rolul switch-ului: **True** daca este root bridge si **False** daca este non-root bridge.



Ce este in plus fata de psuedocod:
cand destinatia unui pachet non-bpdu
este un port trunk cu starea `Blocking`,
atunci arunc pachetul.


## Alte detalii de implementare
---


> *"Bad programmers worry about the code. Good programmers worry about data structures and their relationships."*
> \- Linus Torvalds


Pentru readability, am ales folosirea modului `typing`
pentru a ilustra la nivel de cod niste tipuri de date/clase.
Din stiu eu, la compilare, modulul asta nu are niciun efect, e doar estetic,
dar mult mai intuitiv cand te uiti pe cod (...cel putin mie).


Port-ul unui switch contine urmatoarele informatii:
- Un ID
- Un nume
- Daca este de access la un anume VLAN sau daca este de trunk
- Daca este port trunk, retine si rolul portului:
pentru simplitate, am creat un **Enum** cu urmatoarele valori:
  - `PortState.BLOCKING_PORT`
  - `PortState.DESIGNATED_PORT`
  - `PortState.ROOT_PORT`


Drep pentru care, am create o clasa numita `SwitchPort` care retine aceste informatii.


Pentru a separa port-urile Trunk de cele Access, am creat cat doua clase separate pentru acestea.


> Ar fi o ideea cu adevarat buna daca as fi implementat `Access` si `Trunk` sa mosteneasca `SwitchPort` :))).


Iar pentru a separa rolul port-ului, am creat un **Enum** pentru cele 3 cazuri mentionate mai devreme.



Un switch are:
- Un ID (primul argument *sys.argv[1]* din linia de comanda)
- O prioritate
- O lista de porturi (`SwitchPort`)
- Un ID (prioritate) d.p.d.v. al bridge-ului pentru STP
- Cunoaste ID-ul bridge-ului radacina
- Cunoaste costul catre bridge-ul radacina
- O variabila `is_root_bridge` care atesta switch-ul este sau nu root-bridge (very obvious)


Toate acestea sunt atribute ale clasei `SwitchConfig`.

> O idee si mai buna ar fi ca aceasta clasa sa fi fost si `Singleton`
> (dar asta depaseste cerintele temei).

