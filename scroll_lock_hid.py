#!/usr/bin/env python3
"""
scrolllock_hid_bruteforce.py
Tentativa de vários HID reports para acender/desligar LEDs (Scroll/Num/Caps).
Uso:
  sudo python ~/scrolllock_hid_bruteforce.py on
  sudo python ~/scrolllock_hid_bruteforce.py off
Opções adicionais podem ser adicionadas; essa versão foca em robustez.
"""

import hid
import time
import sys
import logging

# Ajuste para seu teclado
VENDOR_ID = 0xC0F4
PRODUCT_ID = 0x0FF5

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

def pick_keyboard_path():
    cands = []
    for d in hid.enumerate():
        if d.get("vendor_id") == VENDOR_ID and d.get("product_id") == PRODUCT_ID:
            cands.append(d)
    if not cands:
        return None
    # prioriza interface 0 / usage_page 1
    cands.sort(key=lambda x: (x.get("interface_number", 99), x.get("usage_page", 999)))
    for d in cands:
        if d.get("interface_number") == 0 and d.get("usage_page") in (1, None):
            return d["path"]
    return cands[0]["path"]

def try_write(dev, data, label):
    try:
        n = dev.write(bytearray(data))
        logging.info(f"[write] {label}: retornou {n}")
        time.sleep(0.05)
        return True
    except Exception as e:
        logging.debug(f"[write] {label}: ERRO -> {e}")
        return False

def try_feature(dev, data, label):
    try:
        n = dev.send_feature_report(bytearray(data))
        logging.info(f"[feature] {label}: retornou {n}")
        time.sleep(0.05)
        return True
    except Exception as e:
        logging.debug(f"[feature] {label}: ERRO -> {e}")
        return False

def build_attempts(state):
    """
    Retorna uma lista de tuplas (fn, payload, label)
    onde fn é try_write ou try_feature.
    """
    attempts = []
    # formatos básicos
    attempts.append((try_write,  [0x00, state], "write [0x00, state] (Output report ID 0)"))
    attempts.append((try_write,  [state],       "write [state] (Output report sem ReportID)"))
    attempts.append((try_feature,[0x00, state], "feature [0x00, state] (Feature report ID 0)"))
    attempts.append((try_feature,[0x01, state], "feature [0x01, state] (Feature report ID 1)"))
    # report IDs 1..4
    for rid in (1,2,3,4):
        attempts.append((try_write,  [rid, state], f"write [RID={rid}, state]"))
        attempts.append((try_feature,[rid, state], f"feature [RID={rid}, state]"))
    return attempts

def run_attempts(path, on=True, delay=0.05):
    state = 0x01 if on else 0x00  
    logging.info(f"Usando device path: {path!r}")
    dev = hid.device()
    try:
        dev.open_path(path)
    except Exception as e:
        logging.error(f"Erro abrindo device: {e}")
        return False

    try:
        dev.set_nonblocking(1)
    except Exception:
        pass

    attempts = build_attempts(state)

    ok = False
    for fn, payload, label in attempts:
        res = fn(dev, payload, label)
        # interpretamos qualquer tentativa que não jogou exceção como "tentativa feita"
        if res:
            ok = True
        time.sleep(delay)

    dev.close()
    return ok

def main():
    if len(sys.argv) < 2:
        print("Uso: sudo python scrolllock_hid_bruteforce.py on|off")
        return 1
    action = sys.argv[1].lower()
    on = (action != "off")

    path = pick_keyboard_path()
    if not path:
        logging.error("Não achei o dispositivo HID alvo (verifique vendor/product).")
        return 2

    try:
        ok = run_attempts(path, on=on, delay=0.05)
        if ok:
            logging.info("Tentativas concluídas. Verifique LED físico.")
            return 0
        else:
            logging.warning("Nenhuma tentativa reportou sucesso (firmware pode rejeitar).")
            return 3
    except Exception as e:
        logging.exception("Erro inesperado:")
        return 4

if __name__ == "__main__":
    raise SystemExit(main())
