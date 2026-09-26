# SPI Logos Generator for ODR DAB+ multiplexes

100% offline **DAB+ SPI (Service and Programme Information / Logos)** data stream generator for [OpenDigitalRadio (ODR)](https://github.com/Opendigitalradio/) DAB+ multiplexes.
<br>
This is a modified version of ["odr-radiodns-bridge"](https://github.com/nickpiggott/odr-radiodns-bridge) created by [Nick Piggott](https://github.com/nickpiggott/).
<br>
<br>
The modification enables the generation of the SPI data stream without requiring an external web server or a RadioDNS service.
<br>
The aim is to simplify implementation by using a simple local directory of logos.

This script generates a SPI binary carousel compliant with the **ETSI TS 102 371** and **ETSI TS 102 818** specifications.
<br>
Decoding has been tested with success using the [AbracaDABra](https://github.com/KejPi/AbracaDABra) software, and should theoretically work with DAB+ car tuners, although this has not been tested.

---

## Main functions

* **100% Offline:** No DNS resolution or online downloads via RadioDNS. This allows for simpler, local generation of the SPI stream.
* **Automatic data extraction from an ODR-DabMux configuration file:**
  * Automatic detection of all stations in the odr-dabmux configuration file and automatic logo assignment. 
  * Automatic retrieval of long and short labels from the multiplex configuration. 
  * Seamless support for stations with **different ECCs**.
* **Station & Ensemble logo support:** Support for station logos as well as the multiplex's own logo.

---

## Installation instructions

## 📦 1. System Prerequisites and Dependencies

Tested and validated on **Debian 12 (Bookworm)**.

### Essential system packages
```bash
sudo apt update
sudo apt install -y git build-essential python3-dev python3-pip dos2unix
```

### Standard Python libraries
```bash
sudo pip3 install isodate bitarray crcmod pyradiodns dnspython
```

### OpenDigitalRadio-specific libraries
```bash
# ODR Official Python 3 MOT and MSC Modules
sudo pip3 install git+https://github.com/Opendigitalradio/python-dabmot.git 
sudo pip3 install git+https://github.com/Opendigitalradio/python-dabmsc.git

# RadioDNS > ODR Gateway and EPG Structure
sudo pip3 install git+https://github.com/nickpiggott/odr-radiodns-bridge.git
sudo pip3 install git+https://github.com/GlobalRadio/python-mot-epg.git

# Basic SPI library
git clone https://github.com/magicbadger/python-hybridspi.git ~/python-hybridspi
sudo cp -r ~/python-hybridspi/src/spi $(python3 -c "import site; print(site.getsitepackages()[0])")/
sudo chmod -R a+rX $(python3 -c "import site; print(site.getsitepackages()[0])")/spi
```
> The '--break-system-packages' argument might be needed in some cases, at the end of the 'sudo pip3' commands.

---

## 🖼️ 2. Add the logos to a local directory

Place your images in the configured folder (Example: /home/odr/ODR-mmbTools/config/mot/SPI/) or in any other folder of your choice, specified beforehand in the script's configuration section.

### Accepted formats
• PNG: Recommended for transparent logos.
<br>
• JPEG/JPG: Better to ensure full compatibility with all car tuners, since some might have difficulties to decode PNG logos.

### Dimensions and naming

The script automatically searches for logos based on the SIDs (for stations) and the EID (for the ensemble).
<br>
Your logo files must follow a specific naming convention to be correctly identified and assigned:

| Type | Dimensions | Filenames examples | Use |
| :--- | :---: | :--- | :--- |
| **Radio Service (Miniature)** | 32 x 32 | `f9f5-32x32.png` | Small logo in the stations list |
| **Radio Service (Rectangle)** | 112 x 32 | `f9f5-112x32.png` | Display bar on certain car tuners |
| **Radio Service (Square)** | 128 x 128 | `f9f5-128x128.png` | High-resolution square logo on compatible receivers |
| **Radio Service (Wide screen)** | 320 x 240 | `f9f5-320x240.png` | Wide logo displayed before SLS decoding |
| **Multiplex Logo (Miniature)** | 32 x 32 | `f01d-32x32.png` | Small multiplex logo displayed next to its name |
| **Multiplex Logo (Wide screen)** | 320 x 240 | `f01d-320x240.png` | Wide logo for the multiplex |

In the examples above, the radio station SID is F9F5 and is present on a multiplex with F01D EID.
<br>
'.png' can also be replaced by '.jpeg' depending on the logo format. Note that the IDs can be specified in uppercase.
<br>
<br>
32 x 32 and 320 x 240 are the most common dimensions. 112 x 32 is used less frequently.
<br>
You can perfectly well use a single set of dimensions (e.g. 32 x 32 only).

---

## ⚙️ 3. Script configuration

Open ODR-SPI-Generator.py in a text editor and adjust the header variables to match your actual paths.
```python
# ============================================================================ START OF THE USER CONFIGURATION SECTION ============================================================================

CONF_MUX_FILE = "/home/odr/ODR-mmbTools/config/odr-dabmux.info"         # Path to your odr-dabmux file
CONF_LOGOS_DIR = "/home/odr/ODR-mmbTools/config/mot/SPI"                # Path to the folder containing your logos
CONF_OUTPUT_FILE = "/home/odr/ODR-mmbTools/config/mot/spi-output.dat"   # Path to which the output stream (spi-output.dat) is to be generated
CONF_PACKET_SIZE = 48                                                   # Multiple of 3 of the bitrate used for the SPI service in the odr-dabmux config (e.g. 48 for 16 Kbps).
CONF_PACKET_ADDRESS = 1                                                 # SPI packet address (It is recommended to leave it on 1 > 0x1 on the odr-dabmux config file)
CONF_DATAGROUP = False                                                  # Works perfectly with "False" based on tests, only change this value if you really want to.

# ===================================== END OF THE USER CONFIGURATION SECTION - DO NOT MODIFY VALUES BELOW THIS POINT (unless you know what you are doing) ========================================
```

---

### ⚙️ 4. ODR-DabMux file configuration

The easiest way to configure your ODR-DabMux file, including your SPI service, is to use my generator at the following address:
<br>
[https://lucasgallone.github.io/ODR-DabMux-Generator/](https://lucasgallone.github.io/ODR-DabMux-Generator/)
<br>
<br>
Unsure about the values to indicate? Consult the notes in the manual configuration instructions below and apply them in the generator.

If you prefer to configure your setup manually, add the following blocks to your ODR-DabMux configuration file:
<br>
### At the end of the `services` section:
```text
srv-spi {
        id 0xe1f01df1
        label "SPI Logos"
        shortlabel "SPILogos"
    }
```
The 'id' value in this example contains the E1 ECC (`0xe1`), the EID (`f01d`) and two more random hex characters (`f1`)
<br>
In all cases, your SPI service ID must contain 10 hex characters under the following format: `0x'ECC'` + `EID` + `2 additional characters`.
<br>
### At the end of the `subchannels` section:
```text
sub-spi {
        type packet
        bitrate 16
        id 18
        protection-profile EEP_B
        protection 4
        inputproto file
        inputuri "/home/odr/ODR-mmbTools/config/mot/spi-output.dat"
    }
```
• `bitrate` can be adjusted to your desired bitrate: 8, 16, 24, or 32 Kbps.
<br>
• `id` must be modified according to the number of services present on the multiplex. If the last audio service on your multiplex has `id 14`, then you should specify `id 15` for the SPI.
<br>
• `protection-profile` and `protection` must be modified as you see fit, depending on the type of error protection you wish to use.
### At the end of the `components` section:
```text
comp-spi {
        type 60
        service srv-spi
        subchannel sub-spi
        user-applications {
            userapp "spi"
        }
        address 0x1
        datagroup true
    }
```
The `address` value must fit the `CONF_PACKET_ADDRESS` value in the script.
<br>
Example: `address 0x1` in the ODR-DabMux file for `CONF_PACKET_ADDRESS = 1` in the script configuration.

---

### 🚀 5. Using and starting the SPI Generator

The generator only needs to be run once to generate your SPI data stream after placing the logos in your local directory.
<br>
Subsequently, it must be run again whenever logos are added, modified, or deleted.
<br>
<br>
It does not need to be run every time the multiplex starts up if no changes have been made to the logos.

## Manual launch
In a terminal, enter the following command:
```bash
python3 ODR-SPI-Generator.py
```
The generator will analyze your multiplex configuration and the logos in the specified directory, associate them with each radio service, and create the SPI data stream in the binary .dat format, which you can then use on your multiplex.

## Automated startup with Supervisor

You can also use Supervisor to automatize the process startup, which is the recommended option.
<br>
<br>
• Open or create your service file:
> If the path doesn't match, indicate yours instead.
```bash
sudo nano /etc/supervisor/conf.d/dab-spi.conf
```
• Add the following content to the file:
> The command must contain the path where the ODR-SPI-Generator.py file is located. If it doesn't match, indicate yours instead.

> 'user' value might vary depending on your machine configuration. If 'odr' is not the value you use, edit it.
```ini
[program:ODR-SPI-Generator]
command=/usr/bin/python3 /home/odr/ODR-SPI-Generator.py
user=odr
autostart=true
autorestart=false
startsecs=0
stdout_logfile=/var/log/supervisor/ODR-SPI-Generator.log
stderr_logfile=/var/log/supervisor/ODR-SPI-Generator.err.log
```
• Apply the changes:
```bash
sudo supervisorctl reread
sudo supervisorctl update
```

---

### 📄 License
This script is distributed under the GNU General Public License v3.0 (GPLv3). [Click here for more details.](https://github.com/LucasGallone/ODR-SPI-Generator/blob/main/LICENSE)
<br>
<br>
It was developed based on ["odr-radiodns-bridge"](https://github.com/nickpiggott/odr-radiodns-bridge), created by Nick Piggott and distributed under the LGPL 2.1 license.
<br>
As well as the original work by [OpenDigitalRadio](https://github.com/Opendigitalradio/), and adapted for 100% autonomous, offline operation.
