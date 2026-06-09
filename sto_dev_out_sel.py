'''
================================
Storage Device Output Selection
================================

É um programa python que tem a função de extrair as informções das unidades de disco identificadas pelo sistema
para que o usuário possa escolhar entre uma delas, ou não, para assim que o sistema possa salvar os arquivos do 
usuário em outro disco.

'''

import subprocess
import json

def main():
    print("\nEscolha uma opção de aramzenamento para seu uso de sistema: ")
    print("1- Armazenamento Físico\n2- Nenhum\n")

    usr_chose = False
    while usr_chose != True:
        usr_choice = input("Escreva apenas um valor. Ex: \"2\": ")
        
        match usr_choice:
            case '1':
                sto_devices = get_available_devices()
                
                print("\nEscolha uma das unidades de disco disponíveis:")
                device_count = 1
                device_options = {}
                for d in sto_devices:
                    device_options[str(device_count)] = d
                    print(f"{device_count}- Dispositivo: {d["model"]} | Armazenamento Disponível: {d["fsavailable"]}")
                    device_count += 1

                device_chosen = False
                while device_chosen != True:
                    device_choice = input("\nDigite sua opção: ")
                    if device_choice in device_options.keys():
                        try:
                            mount_if_necessary(device_options[device_choice])
                            with open("out_dev.json", "w") as f:
                                json.dump(device_options[device_choice], f, indent=4)
                            print("\nSua escolha foi salva pelo sistema e será utilizada por essa sessão para armazenar todos os arquivos criados.\n")
                        except Exception as error:
                            print(f"\nNaõ foi possível salvar sua escolhar no sistema: {error}")
                        device_chosen = True
                    else:
                        print("\nDigite uma opção válida.\n")   

                usr_chose = True

            case '2':
                yes_list = ('y','Y', '')
                confirm_req = input("Tem certeza de sua opção? Nenhum arquivo salvo no sistema será salvo permanentemente. [Y/n]:\n")
                if confirm_req in yes_list:
                    usr_chose = True
            case _:
                print("\nEscolha uma das opções dispooníveis.\n")
                print("1- Armazenamento Físico\n2- Nenhum\n")

    print("END")

def get_available_devices():
    available_sto_devices = []
    
    out = subprocess.run(["sudo", "lsblk", "-o", "NAME,TYPE,MODEL,PATH,MOUNTPOINTS,UUID,FSSIZE,FSUSED", "-e", "7", "-J"],
                         capture_output=True, text=True, check=True)
    
    out_json = json.loads(out.stdout)
    block_devices =  out_json["blockdevices"]
    
    for d in block_devices:
        if d["type"] == "disk":
            if d["children"] != None:
                for c in d["children"]:
                    if c["uuid"] != None:
                        c["model"] = d["model"]
                        if c["fssize"] and c["fsused"]:
                            c["fsavailable"] = str(round(float(c["fssize"].replace("G", "")) - float(c["fsused"].replace("G", "")), 2)) + "G"
                        else:
                            c["fsavailable"] = "desconhecido"
                        available_sto_devices.append(c)

    return available_sto_devices
                        
def mount_if_necessary(device:dict):
    if len(device["mountpoints"]) == 0:
        mnt_path = "/mnt/temp_dev"
        subprocess.run(["sudo", "mkdir", "-p", mnt_path])
        subprocess.run(["sudo", "mount", device["path"], mnt_path])
    else :
        mnt_path = device["mountpoints"][0]
    with open("/tmp/temp_device_mount", "w") as f:
        f.write(mnt_path)


if __name__ == "__main__":
    main()