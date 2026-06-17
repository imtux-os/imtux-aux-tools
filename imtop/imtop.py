"""
==============
    IMTOP
==============

Um programa que cria uma interface para facilitar o acompanhamento de informações relacionadas a 
elementos de hardware da máquina que execute o sistema operacional IMTUX 
"""

import asyncio
from glob import glob
import json
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.containers import VerticalGroup, HorizontalGroup
from textual.widgets import Footer, Placeholder, Rule, Label, OptionList, Button
from textual.widgets.option_list import Option
from textual.reactive import reactive


class CPUScreen(Screen):
    """ Classe da tela de processador """
    cpu_info = reactive({"Manufacturer": "", "Architecture": "", "Socket Designation": "", "Version": "", "Core Count": "", "Thread Count": "", "max MHz": "", 
                "L1d": "", "L1i": "", "L2": "", "L3": ""})
    cpu_temp = reactive("")
    cpu_clock = reactive({})

    async def parse_info(self) -> None:
        """ Função responsável por ler e descrever informações gerais sobre o processador """
        parse_dmi = await asyncio.create_subprocess_exec(
            "sudo", "dmidecode", "-t", "processor",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        parse_lscpu = await asyncio.create_subprocess_exec(
            "lscpu",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out_dmi, err_dmi = await parse_dmi.communicate()
        out_lscpu, err_lscpu = await parse_lscpu.communicate()
        
        texto = out_dmi.decode() + "\n" + out_lscpu.decode()
        cpu_info_local = {}
        for line in texto.splitlines():
            for k in self.cpu_info.keys():
                if k in line:
                    chave, valor = line.split(":", 1)
                    valor = valor.replace(" ", "")
                    cpu_info_local[k] = valor

        self.cpu_info = cpu_info_local

    async def parse_temp(self) -> float | None:
        """ Função responsável por ler e descrever informações sobre a temperatura do processador """
        for zone in glob("/sys/class/thermal/thermal_zone*"):
            try:
                with open(f"{zone}/type") as f:
                    sensor_type = f.read().strip()

                if sensor_type in ("x86_pkg_temp", "cpu_thermal"):
                    with open(f"{zone}/temp") as f:
                        temp = int(f.read().strip()) / 1000

                    return temp

            except (FileNotFoundError, ValueError):
                continue
    
    async def parse_clock(self) -> float | None:
        """ Função responsável por lçer e descrever informações sobre a frequência de clock dos processadores lógicos """

        # for cpu in ("/sys/devices/system/cpu/cpu" + str(count)):
        clock = {}
        for i in range(0, int(self.cpu_info["Thread Count"])):    
            try:
                with open(f"/sys/devices/system/cpu/cpu{i}/cpufreq/cpuinfo_avg_freq") as f:
                    clock[f"core {i}"] = int(f.read().strip()) / 1000
            
            except (FileNotFoundError, ValueError):
                continue

        return clock
    
    def format_cpu_info(self) -> str:
        """ Função que formata as informações obtidas do processador no texto lido em tela """
        return "\n".join([
            f"Fabricante:        {self.cpu_info.get('Manufacturer', '')}",
            f"Arquitetura:       {self.cpu_info.get('Architecture', '')}",
            f"Soquete:           {self.cpu_info.get('Socket Designation', '')}",
            f"Frequência Máxima: {self.cpu_info.get('max MHz', '')} (MHz)",
            f"Núcleos Físicos:   {self.cpu_info.get('Core Count', '')}",
            f"Núcleos Lógicos:   {self.cpu_info.get('Thread Count', '')}",
        ])

    def format_cpu_cache(self) -> str:
        """ Função que formata as informações obtidas de cache no texto lido em tela """
        return "\n".join([
            f"Dados L1:  {self.cpu_info.get('L1d', '')}",
            f"Inst. L1:  {self.cpu_info.get('L1i', '')}",
            f"Cache L2:  {self.cpu_info.get('L2', '')}",
            f"Cache L3:  {self.cpu_info.get('L3', '')}"
        ])

    def format_cpu_clock(self, value: dict) -> str:
        """ Função que formata as informações obtidas de clock no texto lido em tela """
        clock_str = []
        for k, v in value.items(): 
            clock_str.append(f"{k}: {v}") 
        return "\n".join(clock_str)

    def watch_cpu_info(self) -> None:
        """ Função observadora para aviso a cada atualização de dados gerais da CPU """
        self.query_one("#cpu_text", Label).update(self.format_cpu_info())
        self.query_one("#title_label", Label).update(self.cpu_info.get("Version"))
        self.query_one("#cpu_cache", Label).update(self.format_cpu_cache())

    def watch_cpu_temp(self, value: str) -> None:
        """ Funçã observadora para aviso a cada atualização de temperatura da CPU """
        self.query_one("#cpu_temp", Label).update(f"Temperatura: {value} °C")

    def watch_cpu_clock(self, value: dict) -> None:
        """ Função observadora para aviso a cada atualização de clock da CPU """
        self.query_one("#cpu_clock", Label).update(self.format_cpu_clock(value))

    async def refresh_temp(self) -> None:
        """ Função que roda em um intervalo de 1 segundo para atualizar dados de temperatura """
        temp = await self.parse_temp()

        if temp is not None:
            self.cpu_temp = f"{temp:.1f}"

    async def refresh_clock(self) -> None:
        """ Função que roda em um intervalo de 1 segundo para atualizar dados de frequência """
        clock = await self.parse_clock()

        if clock is not None:
            self.cpu_clock = clock

    def refresh_master(self) -> None:
        self.run_worker(self.refresh_temp())
        self.run_worker(self.refresh_clock())

    def compose(self) -> ComposeResult:
        yield Label(content= "", id="title_label")
        with VerticalGroup():
            
            with HorizontalGroup():
                with VerticalGroup(id="cpu_text_panel"):
                    yield Label(content="", id="cpu_text")
                with VerticalGroup(id="cpu_temp_panel"):
                    yield Label(content="Temperatura: 0.0", id="cpu_temp")
            
            yield Rule(line_style="heavy")
            
            with HorizontalGroup():
                with VerticalGroup(id="cpu_cache_panel"):
                    yield Label(content="", id="cpu_cache")
                with VerticalGroup(id="cpu_clock_panel"):
                    yield Label(content="", id="cpu_clock")
        yield Footer()

    async def on_mount(self) -> None:
        await self.parse_info()
        self.set_interval(1.0, self.refresh_master)
        self.query_one("#cpu_text_panel").border_title = "Geral"
        self.query_one("#cpu_temp_panel").border_title = "Temperatura"
        self.query_one("#cpu_cache_panel").border_title = "Cache"
        self.query_one("#cpu_clock_panel").border_title = "Frequências de Clock (MHz)"
                

class MemScreen(Screen):
    """ Classe da tela de memória """
    mem_info = reactive({"Total": "", "Available": "", "Cached": "", "Size": [], "Form Factor": [], "Locator": [], "Type": [], 
                         "Speed": [], "Serial": [], "Manufacturer": [], "Part Num": []})

    def  kb_to_gib(self, mem: str) -> str:
        kb = int(mem.split()[0])
        return f"{kb / 1024 / 1024:.1f} GiB"
    
    async def parse_mem(self) -> None:
        parse_dmi = await asyncio.create_subprocess_exec(
            "sudo", "dmidecode", "-t", "17",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out_dmi, err_dmi = await parse_dmi.communicate()

        mem_info_local = {"Total": "", "Available": "", "Cached": "", "Size": [], "Form Factor": [], "Locator": [], "Type": [], 
                         "Speed": [], "Serial": [], "Manufacturer": [], "Part Num": []}
        
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_info_local["Total"] = self.kb_to_gib(line.split(":", 1)[1].strip().replace("kB", ""))

                elif line.startswith("MemAvailable:"):
                    mem_info_local["Available"] = self.kb_to_gib(line.split(":", 1)[1].strip().replace("kB", ""))

                elif line.startswith("Cached:"):
                    mem_info_local["Cached"] = self.kb_to_gib(line.split(":", 1)[1].strip().replace("kB", ""))

        texto = out_dmi.decode()

        devices = []
        current = None
   
        for line in texto.splitlines():
            line = line.strip()

            if line == "Memory Device":
                if current is not None:
                    devices.append(current)
                current = {}
                continue

            if current is not None and ":" in line:
                key, value = line.split(":", 1)
                current[key.strip()] = value.strip()

        if current is not None:
            devices.append(current)

        for dev in devices:
            if dev.get("Size") == "No Module Installed":
                continue

            mem_info_local["Size"].append(
                dev.get("Size", "")
            )

            mem_info_local["Form Factor"].append(
                dev.get("Form Factor", "")
            )

            mem_info_local["Locator"].append(
                dev.get("Locator", "")
            )

            mem_info_local["Type"].append(
                dev.get("Type", "")
            )

            mem_info_local["Speed"].append(
                dev.get(
                    "Configured Memory Speed",
                    dev.get("Speed", "")
                )
            )

            mem_info_local["Manufacturer"].append(
                dev.get("Manufacturer", "")
            )

            mem_info_local["Serial"].append(
                dev.get("Serial Number", "")
            )

            mem_info_local["Part Num"].append(
                dev.get("Part Number", "")
            )


        self.mem_info = mem_info_local

    def format_mem_info(self, value: dict) -> str:
        texto = [
            f"Memória Total:      {value.get('Total', '')}",
            f"Memória Disponível: {value.get('Available', '')}",
            f"Memória em Cache:   {value.get('Cached', '')}",
        ]

        if value.get("Type"):
            texto.append(f"Geração da Memória: {value['Type'][0]}")

        texto.append("")
        texto.append("Módulos Instalados")
        texto.append("------------------")

        for i in range(len(value.get("Size", []))):
            texto.extend([
                f"Slot {i + 1}",
                f"  Tamanho:     {value['Size'][i]}",
                f"  Localização: {value['Locator'][i]}",
                f"  Tipo:        {value['Type'][i]}",
                f"  Velocidade:  {value['Speed'][i]}",
                f"  Fabricante:  {value['Manufacturer'][i]}",
                f"  Serial:      {value['Serial'][i]}",
                f"  Part Number: {value['Part Num'][i]}",
                ""
            ])

        return "\n".join(texto)
    
    def watch_mem_info(self, value:dict) -> None:
        self.query_one("#mem_info", Label).update(self.format_mem_info(value))
    
    def compose(self) -> ComposeResult:
        with VerticalGroup():
            yield Label(content="", id="mem_info")
        yield Footer()

    async def on_mount(self) -> None:
        await self.parse_mem()


class StoScreen(Screen):
    """ Classe da tela de unidades de disco """
    sto_devices = reactive({})

    async def mount_sto_option(self) -> None:
        """ Função responsãvel por adicionar as opções de unidades de disco à lista """
        parse_lsblk = await asyncio.create_subprocess_exec(
            "lsblk", "-J", "-e", "1,7", "-do", "NAME,SIZE,MODEL,SERIAL,MOUNTPOINTS",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out_lsblk, err_lsblk = await parse_lsblk.communicate()
        
        data = json.loads(out_lsblk.decode())
        devs = {}
        for b in data["blockdevices"]:
            if not "zram" in b["name"]:
                devs[b["name"]] = {
                                    "size": b["size"],
                                    "mount": b["mountpoints"],
                                    "model": b.get("model", ""),
                                    "serial":  b.get("serial", "")
                                }

        for dev_name, dev_info in devs.items():
            mounts = dev_info["mount"]
            if mounts and mounts[0]:
                mountpoint = mounts[0]
                parse_df = await asyncio.create_subprocess_exec(
                    "df",
                    "-h",
                    mountpoint,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                out_df, err_df = await parse_df.communicate()

                texto_df = out_df.decode()
                for line in texto_df.splitlines():
                    if mountpoint in line:
                        line_split = line.split()
                        if len(line_split) >= 5:
                            dev_info["used"] = line_split[2]
                            dev_info["avail"] = line_split[3]
                            dev_info["use%"] = line_split[4]
            
            parse_hdparm = await asyncio.create_subprocess_exec(
                "sudo",
                "hdparm",
                "-i",
                f"/dev/{dev_name}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            out_hdparm, err_hdparm = await parse_hdparm.communicate()

            texto_hdparm = out_hdparm.decode()
            for line in texto_hdparm.splitlines():
                if line.startswith("Model="):
                    parts = line.split(",")
                    for part in parts:
                        part = part.strip()
                        if part.startswith("FwRev="):
                            dev_info["fwm"] = part.removeprefix("FwRev=")

        self.sto_devices = devs

    def watch_sto_devices(self, value: dict) -> None:
        option_list = self.query_one("#sto_options", OptionList)
        option_list.clear_options()

        for dev_name, dev_info in value.items():
            model = dev_info.get("model", "").strip()
            if model:
                text = f"{model} ({dev_name})" 
            else: 
                text = dev_name

            option_list.add_option(Option(text, id=dev_name))

    def format_sto_info(self, dev_name: str) -> str:
        dev = self.sto_devices[dev_name]

        return "\n".join([
            f"Dispositivo: {dev_name}",
            f"Modelo: {dev.get('model', '')}",
            f"Tamanho: {dev.get('size', '')}",
            f"Série: {dev.get('serial', '')}",
            f"Firmware: {dev.get('fwm', '')}",
            f"Utilizado: {dev.get('used', 'N/A')}",
            f"Disponível: {dev.get('avail', 'N/A')}",
            f"Uso: {dev.get('use%', 'N/A')}",
        ])

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        dev_name = event.option.id

        self.query_one("#sto_info", Label).update(
            self.format_sto_info(dev_name)
        )

    def compose(self) -> ComposeResult:
        yield OptionList(id="sto_options")
        yield Label(content="Selecione um dispositivo", id="sto_info")
        yield Footer()

    async def on_mount(self) -> None:
        await self.mount_sto_option()


class NetScreen(Screen):
    """ Classe da tela de rede """
    def compose(self) -> ComposeResult:
        yield Placeholder("NET")
        yield Footer()


class ImtopApp(App):
    """ Classe de Aplicação """

    CSS_PATH = "imtopCSS.tcss"

    BINDINGS = [
        ("1", "switch_mode('cpu')", "Processador"),
        ("2", "switch_mode('mem')", "Memória"),
        ("3", "switch_mode('sto')", "Unidades de Disco"),
        ("4", "switch_mode('net')", "Rede")
    ]

    MODES = {
        "cpu": CPUScreen,
        "mem": MemScreen,
        "sto": StoScreen,
        "net": NetScreen
    }

    def on_mount(self) -> None:
        self.switch_mode("cpu")


if __name__ == "__main__":
    app = ImtopApp()
    app.run()