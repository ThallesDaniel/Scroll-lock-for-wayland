import hid
import time
import sys


'''
Para ligar o LED:
sudo python ~/scrolllock_hid_bruteforce.py on
Para desligar o LED:
sudo python ~/scrolllock_hid_bruteforce.py off
'''

VENDOR_ID = 0xC0F4
PRODUCT_ID = 0x0FF5

def pick_keyboard_path():
    # Prioriza interface 0 (Keyboard), usage_page 1, usage 6
    cands = []
    for d in hid.enumerate():
        if d.get('vendor_id') == VENDOR_ID and d.get('product_id') == PRODUCT_ID:
            cands.append(d)
    # Ordena para pegar interface 0 primeiro
    cands.sort(key=lambda x: (x.get('interface_number', 99), x.get('usage_page', 999)))
    for d in cands:
        if d.get('interface_number') == 0 and d.get('usage_page') in (1, None):
            return d['path']
    # fallback: primeiro da lista
    return cands[0]['path'] if cands else None

def try_write(dev, data, label):
    try:
        n = dev.write(bytearray(data))
        print(f"[write] {label}: retornou {n}")
        time.sleep(0.05)
        return True
    except Exception as e:
        print(f"[write] {label}: ERRO -> {e}")
        return False

def try_feature(dev, data, label):
    try:
        n = dev.send_feature_report(bytearray(data))
        print(f"[feature] {label}: retornou {n}")
        time.sleep(0.05)
        return True
    except Exception as e:
        print(f"[feature] {label}: ERRO -> {e}")
        return False

def main(on=True):
    path = pick_keyboard_path()
    if not path:
        print("Não achei o hidraw do teclado alvo (C0F4:0FF5).")
        sys.exit(1)

    print(f"Usando device path: {path!r}")

    state = 0x01 if on else 0x00

    dev = hid.device()
    dev.open_path(path)
    # Alguns firmwares pedem não-bloqueante
    try:
        dev.set_nonblocking(1)
    except Exception:
        pass

    # Tentativas comuns
    attempts = [
        (try_write,        [0x00, state],              "write [0x00, state] (Output report c/ ReportID 0)"),
        (try_write,        [state],                    "write [state] (Output report sem ReportID)"),
        (try_feature,      [0x00, state],              "feature [0x00, state] (Feature report ID 0)"),
        (try_feature,      [0x01, state],              "feature [0x01, state] (Feature report ID 1)"),
    ]

    # Alguns teclados usam report IDs 1..4 para LEDs
    for rid in (1, 2, 3, 4):
        attempts.append((try_write,   [rid, state],    f"write [RID={rid}, state]"))
        attempts.append((try_feature, [rid, state],    f"feature [RID={rid}, state]"))

    ok = False
    for fn, payload, label in attempts:
        if fn(dev, payload, label):
            ok = True
        time.sleep(0.05)

    dev.close()

    if ok:
        print("Terminei as tentativas. Veja se o LED mudou (alguns modelos aplicam após ~100ms).")
    else:
        print("Nenhuma chamada retornou sucesso. Pode ser que o firmware rejeite comandos diretos de LED.")

if __name__ == "__main__":
    action = "on"
    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
    main(on=(action != "off"))
