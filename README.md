# README — ScrollLock HID Controller (Português)

**Descrição curta**
Script Python que comunica diretamente com o teclado via HID para ativar/desativar o LED de **Scroll Lock** no firmware do dispositivo. Resolve casos em que o compositor Wayland / kernel não permite controlar o LED por `sysfs` ou `hyprctl`. NÃO altera o estado lógico do sistema (ou seja, aplicações podem continuar vendo ScrollLock como *off*).

---

## Índice

* O que é e por que existe
* Funciona com Wayland? (explicação)
* Recursos / limitações
* Requisitos / dependências
* Instalação rápida
* Uso (comandos)
* Iniciar no boot (systemd)
* Permitir execução sem `sudo` (udev rule)
* Diagnóstico e troubleshooting
* Segurança e cuidados
* Licença

---

## O que é e por que existe

Alguns teclados USB (firmwares específicos) só acendem o LED físico de Scroll Lock quando recebem um **relatório HID** específico do host, ignorando escritas diretas em `/sys/class/leds/.../brightness`. Em ambientes Wayland (Hyprland, Sway, etc.) o compositor pode não propagar/gerenciar o estado lógico do Scroll Lock, fazendo com que `echo 1 > .../brightness` apenas pisque o LED.
Este projeto envia relatórios HID diretamente ao dispositivo para forçar o LED no nível do firmware, contornando limites do compositor/kernel.

---

## Funciona com Wayland?

Sim. Em Wayland o compositor frequentemente controla o "estado lógico" de locks e pode não expor rotas simples para manipular o LED fisicamente. O script **fala diretamente com o dispositivo HID (/dev/hidraw*)**, ignorando o compositor e o subsistema `input` do kernel — logo funciona independentemente do Wayland/Xorg.
**Nota importante:** isso controla apenas o LED físico no firmware do teclado; não necessariamente altera o “estado lógico” (o que apps recebem como ScrollLock). Para mudar o estado lógico, seria necessário enviar eventos de teclado ao kernel/compositor (ex.: ydotool/setleds/hyprctl), que em Wayland às vezes não funcionam consistentemente.

---

## Recursos / Limitações

* ✅ Força o LED de Scroll Lock via HID report diretamente ao teclado.
* ✅ Funciona em Wayland (quando sysfs/hid/ou hyprctl falham).
* ✅ Permite serviço systemd para acender no boot.
* ❌ **Não** altera o estado lógico do sistema (teclado pode continuar “off” para apps).
* ❌ Requer acesso a `/dev/hidraw*` (normalmente root), a não ser que se adicione uma regra `udev` para permissões.
* ❌ Nem todos os teclados aceitam todos os formatos de report — o repositório inclui tentativa “bruteforce” de formatos comuns.

---

## Requisitos / Dependências

* Python 3 (recomendado >= 3.8)
* Biblioteca HID Python:

  * No Arch/Garuda: `python-hidapi` (`pacman -S python-hidapi`)
  * Alternativa: `pip install hid` (ou `pip install hidapi`)
* Acesso ao dispositivo HID (`/dev/hidrawX`). Normalmente `sudo` é necessário sem regra udev.
* (Opcional) `systemd` para serviço de boot.

---

## Instalação rápida

1. Clone / crie o arquivo do script:

```bash
# no seu home
nano ~/scrolllock_hid_bruteforce.py
# cole o script (o fornecido anteriormente que tenta múltiplos formatos)
# salve e saia
chmod +x ~/scrolllock_hid_bruteforce.py
```

2. Instale a dependência:

```bash
# Arch/Garuda
sudo pacman -S python-hidapi

# ou com pip se necessário
pip install hid
```

3. Teste a enumeração (confirma VENDOR/PRODUCT):

```bash
python - <<'PY'
import hid
for d in hid.enumerate():
    print(d)
PY
```

Anote `vendor_id` / `product_id` / `path` (ex.: `/dev/hidraw1`) caso queira ajustar o script.

---

## Uso

* Ligar o LED:

```bash
sudo python ~/scrolllock_hid_bruteforce.py on
```

* Desligar o LED:

```bash
sudo python ~/scrolllock_hid_bruteforce.py off
```

* Observações:

  * Use `sudo` para garantir acesso a `/dev/hidraw*`.
  * Caso prefira, o script pode ser chamado por um wrapper shell ou serviço systemd.

---

## Iniciar no boot (systemd)

Exemplo de unit systemd (acende uma vez no boot usando o script):

```bash
sudo tee /etc/systemd/system/scrolllock-hid.service > /dev/null <<'EOF'
[Unit]
Description=Set ScrollLock LED via HID brute-force

[Service]
Type=oneshot
ExecStart=/usr/bin/python /home/<seu_usuario>/scrolllock_hid_bruteforce.py on

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now scrolllock-hid.service
```

Substitua `/home/<seu_usuario>/scrolllock_hid_bruteforce.py` pelo caminho correto.

---

## Permitir execução sem `sudo` (udev rule)

Para evitar `sudo` toda vez, crie uma regra `udev` que dê permissão ao grupo `hidusers` (ou similar).

1. Crie grupo (uma vez):

```bash
sudo groupadd -f hidusers
sudo usermod -aG hidusers $USER
```

2. Crie regra udev:

```bash
sudo tee /etc/udev/rules.d/99-hidraw-perms.rules > /dev/null <<'EOF'
KERNEL=="hidraw*", SUBSYSTEM=="hidraw", MODE="0660", GROUP="hidusers"
EOF
```

3. Recarregue:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Depois faça logout/login para que o usuário entre no grupo, e então o script poderá abrir `/dev/hidraw*` sem `sudo`.

**Atenção:** Dar permissão a `hidraw` permite leitura/escrita de dispositivos HID — avalie o risco segurança.

---

## Diagnóstico e troubleshooting

* **Nada acontece e script retorna sucesso:** verifique se o `hid.enumerate()` mostra seu teclado e qual `path` ele usa.
* **Verificando `hid` devices:**

```bash
python - <<'PY'
import hid
for d in hid.enumerate():
    print(d)
PY
```

* **Testar leitura/escrita hidraw diretamente:**

```bash
ls -l /dev/hidraw*
sudo cat /sys/class/leds/*scroll*/brightness
```

* **Se `echo 1 > /sys/class/leds/...` muda o valor mas o LED não acende:** indica que o kernel aceitou alteração mas o firmware ignora — então o método HID é o caminho correto.
* **Se nem o script nem `echo` produzem mudança:** verifique permissões, se outro processo mantém o dispositivo aberto, ou se o teclado tem mecanismo proprietário (alguns precisam de driver/OpenRGB).

---

## Segurança e cuidados

* Acessar `/dev/hidraw*` exige confiança no código: você está enviando bytes ao firmware do teclado. Use apenas scripts do qual confia a origem.
* Udev rules que relaxam permissões aumentam a superfície de ataque para leitura/escrita de dispositivos HID. Proteja sua conta e evite internet/executáveis desconhecidos.
* Teste primeiro com `python` em sessão interativa e veja saídas antes de habilitar no boot.

---

## Como funciona (resumo técnico)

1. O script localiza o dispositivo HID (por vendor/product ou por path).
2. Abre o hidraw via hidapi (binding Python).
3. Envia *output reports* ou *feature reports* comuns usados por muitos firmwares para controlar LEDs. Formatos típicos:

   * `[0x00, state]` (Report ID 0 + bits)
   * `[state]` (sem Report ID)
   * `[report_id, state]` (report IDs 1..4)
   * `send_feature_report([rid, state])`
     onde `state` = bitmask: Scroll = `0x01`, Num = `0x02`, Caps = `0x04`.
4. Se o teclado aceitar o formato, seu firmware altera o LED físico.

---

## Exemplos práticos

* Ligar Scroll Lock via Python:

```bash
sudo python ~/scrolllock_hid_bruteforce.py on
```

* Alternar via alias (`~/.bashrc`):

```bash
alias scroll-on='sudo python ~/scrolllock_hid_bruteforce.py on'
alias scroll-off='sudo python ~/scrolllock_hid_bruteforce.py off'
```

---

## FAQ rápido

* **Isso faz o ScrollLock “funcionar” para programas?**
  Não. Ele só liga o LED no firmware. Para que programas vejam o estado lógico, o kernel/compositor precisa ter o lock ativo.
* **O script funciona em qualquer teclado?**
  Não — funciona em muitos teclados genéricos e em vários modelos com VID/PID compatíveis. Alguns firmwares não aceitam reports externos.
* **Preciso de root sempre?**
  Por padrão sim (acesso ao hidraw). Pode-se criar regra udev para evitar `sudo`.

---

## Contribuição

Pull requests e issues são bem-vindos. Se você tiver um layout de HID report que funcionou para um modelo específico, abra uma issue ou PR com os detalhes (VID/PID, payload usado).

---

## Licença

MIT License — veja o arquivo `LICENSE` para detalhes.

---

---

---

# README — ScrollLock HID Controller (ENGLISH)

**Short description**
Python script that communicates directly with the keyboard over HID to enable/disable the **Scroll Lock** LED in the device firmware. It solves cases where the Wayland compositor / kernel does not allow controlling the LED via `sysfs` or `hyprctl`. It does NOT change the system logical lock state (apps may still see ScrollLock as *off*).

---

## Index

* What it is and why it exists
* Does it work with Wayland? (explanation)
* Features / limitations
* Requirements / dependencies
* Quick installation
* Usage (commands)
* Start at boot (systemd)
* Allow running without `sudo` (udev rule)
* Diagnosis and troubleshooting
* Security and precautions
* License

---

## What it is and why it exists

Some USB keyboards (specific firmwares) only light the physical Scroll Lock LED when they receive a specific **HID report** from the host, ignoring direct writes to `/sys/class/leds/.../brightness`. In Wayland environments (Hyprland, Sway, etc.) the compositor may not propagate/manage the logical Scroll Lock state, causing `echo 1 > .../brightness` to only blink the LED.
This project sends HID reports directly to the device to force the LED at the firmware level, bypassing compositor/kernel limitations.

---

## Does it work with Wayland?

Yes. On Wayland the compositor often controls the logical lock state and may not expose simple ways to physically manipulate keyboard LEDs. The script **talks directly to the HID device (/dev/hidraw*)**, bypassing the compositor and the kernel input subsystem — therefore it works regardless of Wayland/Xorg.
**Important note:** this controls only the physical LED in the keyboard firmware; it does not necessarily change the “logical” state (what apps receive as ScrollLock). To change the logical state you would need to send keyboard events to the kernel/compositor (e.g., ydotool/setleds/hyprctl), which on Wayland can be inconsistent.

---

## Features / Limitations

* ✅ Forces the Scroll Lock LED via HID report directly to the keyboard.
* ✅ Works on Wayland when sysfs/hid/or hyprctl fail.
* ✅ Supports a systemd service for boot activation.
* ❌ **Does not** change the system logical lock state (apps may still see it as off).
* ❌ Requires access to `/dev/hidraw*` (usually root) unless a udev rule is added.
* ❌ Not all keyboards accept all report formats — repository includes a brute-force attempt for common formats.

---

## Requirements / Dependencies

* Python 3 (recommended >= 3.8)
* Python HID library:

  * On Arch/Garuda: `python-hidapi` (`pacman -S python-hidapi`)
  * Alternative: `pip install hid` (or `pip install hidapi`)
* Access to HID device (`/dev/hidrawX`). Typically `sudo` is required without a udev rule.
* (Optional) `systemd` for boot service.

---

## Quick installation

1. Create the script file:

```bash
# in your home
nano ~/scrolllock_hid_bruteforce.py
# paste the provided script (tries multiple formats)
# save and exit
chmod +x ~/scrolllock_hid_bruteforce.py
```

2. Install dependency:

```bash
# Arch/Garuda
sudo pacman -S python-hidapi

# or with pip if needed
pip install hid
```

3. Test enumeration (confirm VENDOR/PRODUCT):

```bash
python - <<'PY'
import hid
for d in hid.enumerate():
    print(d)
PY
```

Note `vendor_id` / `product_id` / `path` (e.g. `/dev/hidraw1`) if you need to adjust the script.

---

## Usage

* Turn the LED on:

```bash
sudo python ~/scrolllock_hid_bruteforce.py on
```

* Turn the LED off:

```bash
sudo python ~/scrolllock_hid_bruteforce.py off
```

* Notes:

  * Use `sudo` to ensure access to `/dev/hidraw*`.
  * You can wrap the script in a shell alias or call it from systemd.

---

## Start at boot (systemd)

Example systemd unit (runs once at boot to set LED):

```bash
sudo tee /etc/systemd/system/scrolllock-hid.service > /dev/null <<'EOF'
[Unit]
Description=Set ScrollLock LED via HID brute-force

[Service]
Type=oneshot
ExecStart=/usr/bin/python /home/<your_user>/scrolllock_hid_bruteforce.py on

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now scrolllock-hid.service
```

Replace `/home/<your_user>/scrolllock_hid_bruteforce.py` with the correct path.

---

## Allow running without `sudo` (udev rule)

To avoid using `sudo` every time, create a udev rule that grants access to a group like `hidusers`.

1. Create group (once):

```bash
sudo groupadd -f hidusers
sudo usermod -aG hidusers $USER
```

2. Create udev rule:

```bash
sudo tee /etc/udev/rules.d/99-hidraw-perms.rules > /dev/null <<'EOF'
KERNEL=="hidraw*", SUBSYSTEM=="hidraw", MODE="0660", GROUP="hidusers"
EOF
```

3. Reload:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then logout/login so your user is in the group and the script can open `/dev/hidraw*` without `sudo`.

**Warning:** Giving permissions to `hidraw` allows read/write access to HID devices — evaluate security risks.

---

## Diagnosis and troubleshooting

* **Nothing happens but script returns success:** check `hid.enumerate()` output to see which path the keyboard uses.
* **List HID devices:**

```bash
python - <<'PY'
import hid
for d in hid.enumerate():
    print(d)
PY
```

* **Test hidraw directly:**

```bash
ls -l /dev/hidraw*
sudo cat /sys/class/leds/*scroll*/brightness
```

* **If `echo 1 > /sys/class/leds/...` changes the value but the LED doesn’t light:** kernel accepted the write but firmware ignores it — HID method is correct.
* **If neither script nor `echo` produce changes:** check permissions, if another process holds the device, or if the keyboard uses a proprietary protocol (some need OpenRGB/drivers).

---

## Security and precautions

* Accessing `/dev/hidraw*` requires trust in the code: you are sending raw bytes to keyboard firmware. Use only trusted scripts.
* Udev rules that relax permissions increase attack surface for HID read/write. Protect your account and avoid running unknown binaries.
* Test interactively before enabling at boot.

---

## How it works (technical summary)

1. The script locates the HID device (by vendor/product or path).
2. Opens the hidraw device via hidapi (Python binding).
3. Sends output reports or feature reports commonly used by firmwares to control LEDs. Typical formats:

   * `[0x00, state]` (Report ID 0 + bits)
   * `[state]` (no Report ID)
   * `[report_id, state]` (report IDs 1..4)
   * `send_feature_report([rid, state])`
     where `state` bitmask: Scroll = `0x01`, Num = `0x02`, Caps = `0x04`.
4. If the keyboard accepts the format, firmware toggles the physical LED.

---

## Practical examples

* Turn on Scroll Lock via Python:

```bash
sudo python ~/scrolllock_hid_bruteforce.py on
```

* Toggle via alias (`~/.bashrc`):

```bash
alias scroll-on='sudo python ~/scrolllock_hid_bruteforce.py on'
alias scroll-off='sudo python ~/scrolllock_hid_bruteforce.py off'
```

---

## Quick FAQ

* **Does this make ScrollLock “work” for programs?**
  No. It only lights the firmware LED. For programs to see the logical lock state, kernel/compositor must have the lock active.
* **Will it work on any keyboard?**
  No — works on many generic keyboards and various models with compatible VID/PID. Some firmwares reject external reports.
* **Do I always need root?**
  By default yes (hidraw access). You can add a udev rule to avoid `sudo`.

---

## Contributing

PRs and issues welcome. If you have a HID report that worked for a specific model, open an issue/PR with VID/PID and payload used.

---

## License

MIT License — see `LICENSE` for details.
