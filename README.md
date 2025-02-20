# <img src="https://www.svgrepo.com/show/354258/raspberry-pi.svg" alt="Raspberry Pi Logo" width="40" height="40" style="vertical-align:middle" /> **GPS Data Viewer** <img src="https://www.svgrepo.com/show/223049/maps-gps.svg" alt="Maps GPS Logo" width="40" height="40" style="vertical-align:middle" />

Setup and configuration of a GPS tracker project running on a Raspberry Pi 3B (`bcm2837-rpi-3-b`) platform.
It includes details on how the **RootFS**, **custom Kernel**, **Overlay** structure, and the **App Daemon** for GPS data collection and display were implemented.

> **References**:
>
> - [🌱 Buildroot Official Site](https://github.com/buildroot/buildroot) (latest version)
> - [🐧 Linux Kernel Source](https://github.com/torvalds/linux)  
> - [🔗 Buildroot Documentation](https://buildroot.org/docs.html)
>

Below is the layout of the project’s files and directories, as seen in the screenshot. All **Buildroot** configuration details are found in **`buildroot_config`**, while all **Linux kernel** configuration details reside in **`kernel_config`**.

```bash
/
├── bin 
│   ├── bcm2837-rpi-3-b.dtb             # Device Tree Blob for Raspberry Pi 3B
│   ├── gps-emu.py                      # GPS emulator script
│   ├── launch-tema2.sh                 # Boot script for launching the OS
│   ├── tema2.img                       # OS image for Raspberry Pi 3B
│   └── vmlinuz-tema2                   # Custom Linux kernel image
│
├── src
│   ├── raspberrypi3-64-overlay         # Overlay directory for Buildroot
│   │   ├── etc                         # System configuration files
│   │   │   ├── init.d
│   │   │   │   ├── S68gps-daemon       # Startup script for GPS daemon
│   │   │   │   └── S70gps-server       # Startup script for GPS web server
│   │   │   ├── ssh
│   │   │   │   └── sshd_config         #== SSH server configuration
│   │   │   ├── udev
│   │   │   │   └── rules.d
│   │   │   │       └── mama_mea.rules  #== Rules for Ethernet starting correctly
│   │   │   ├── passwd                  # Password file for user authentication
│   │   │   └── shadow                  # Hashed passwords for users
│   │   │
│   │   ├── opt
│   │   │   ├── templates
│   │   │   │   └── index.html          #== Web interface for GPS data
│   │   │   ├── gps-daemon.py           #== Script that collects GPS data
│   │   │   └── gps-server.py           #== Flask server for GPS data visualization
│   │   │
│   │   └── tmp
│   │       └── #== JSON files will be created when OS starts
│   │
│   ├── buildroot_config                #== Buildroot configuration file
│   ├── kernel_config                   #== Linux kernel configuration file
│   ├── checksum.txt                    #== Checksum bin_archive.tar.xz
│   ├── Makefile                        #== QEMU Makefile, generates tema2.img, vmlinuz-tema2, bcm2837-rpi-3-b.dtb, ...
│   ├── requirements.txt                #== Requirements for emulating USB Serial
│   └── url.txt                         #== URL with bin_archive.tar.xz (&download=1)
\
```

**Explanation:**

1. **`bin/`**: Contains compiled binaries and scripts necessary for system operation.
2. **`assets/`**: May store disk images, icons, or other graphical assets.
3. **`src/raspberrypi3-64-overlay/`**: The overlay directory for **Buildroot**, containing:
   - `etc/`: System configuration files.
   - `opt/`: Python scripts and web-related files.
   - `tmp/`: Temporary storage.
4. **`buildroot_config`**: Stores **all Buildroot settings**, including selected packages, toolchain options, and other Buildroot-specific parameters.
5. **`kernel_config`**: Contains the **Linux kernel configuration**, specifying which drivers, modules, and features are compiled into the custom kernel.

---

## 🌍 GPS Data Viewer - GGA, GSA, GSV, GLL, Map, HDT, RMC, VTG, ZDA

<div align="center">
    <img src="/assets/gga_gsa_gsv_gll_map.png" alt="GPS Data Viewer - GGA, GSA, GSV, GLL, and Map" width="900px">
    <br>
    <img src="/assets/map_hdt_rmc_vtg_zda.png" alt="GPS Data Viewer - Map, HDT, RMC, VTG, ZDA" width="900px">
</div>

---

## 1. Root Filesystem (RootFS) 📁

### 1.1. Overview

- The RootFS (`rootfs.ext4`) was generated using **Buildroot** (latest version from GitHub) for the Raspberry Pi 3B (64-bit) platform (`bcm2837-rpi-3-b`).
- The official `raspberrypi3_64_defconfig` was used as a starting point, then extended with custom settings to satisfy the project requirements.
- The final RootFS is **256 MB** in size and contains all the essential components for running the GPS and web services.

**Buildroot Configuration Highlights**:

1. **Cross-Compilation**: Buildroot automatically cross-compiles the entire userspace for the ARMv8 architecture (64-bit).
2. **Filesystem Format**: The output is an EXT4 filesystem image (`rootfs.ext4`), suitable for mounting as the root partition on an SD card.
3. **Customization**: By selecting or deselecting packages in the Buildroot menuconfig, the final size and capabilities of the image are controlled.

### 1.2. Essential Packages and Settings

Several packages were added to fulfill project functionality:

- **Avahi-daemon** 🌐  
  - Provides mDNS support, allowing network access via the hostname `tema2.local` (with password `tema2`).  
  - This makes local network discovery simpler, removing the need to track DHCP-assigned IPs manually.

- **Python 3** and **pip** 🐍  
  - Required for running both the HTTP application (Flask) and the GPS daemon (`gps-daemon.py`).  
  - Pip helps manage Python dependencies (e.g., installing `pyserial` or other needed libraries).

- **Flask** 🍃  
  - A micro web framework for implementing the server used to display GPS data in real time.  
  - Chosen for its ease of setup and lightweight footprint.

- **OpenSSH and AutoSSH** 🔐  
  - Enables secure remote access (SSH), so you can log into the device for maintenance or debugging.  
  - AutoSSH can automatically re-establish port forwarding tunnels if the connection is interrupted.

- **DHCP Client** ⚙️  
  - Configured to obtain an IP address on the `eth0` interface automatically.  
  - Simplifies networking, especially in dynamic or unknown environments.

**Additional RootFS Details**:

- **Init Scripts**: The overlay includes scripts in `/etc/init.d` (specifically numbered `68` and `70`) to ensure they start in the correct order, avoiding conflicts with other services.
- **User and Password**: The default user or root credentials can be set. In this case, `tema2` is used as the password, stored as an MD5 hash in `/etc/shadow`.
- **Backup Config**: A backup of kernel or Buildroot configurations may be stored for reference (e.g., `config_tema2.txt`).

---

## 2. Overlay Structure 🏗️

***(Additional reference for how the custom files are merged into the final RootFS.)***

1. **`/etc` Directory**:  
   - Initialization scripts (`init.d/`) with unique numbering to avoid collisions.  
   - `passwd` and `shadow` files store authentication details.  
   - `ssh` config ensures OpenSSH starts properly.  
   - `udev/rules.d/mama_mea.rules` enforces consistent naming for `eth0`.

2. **`/opt` Directory**:  
   - **`gps-daemon`**: Contains the Python script that reads and processes GPS data.  
   - **`gps-server`**: Contains the Flask-based web server script for displaying real-time GPS info.  
   - **`templates/index.html`**: The HTML template for the GPS visualization page.

3. **`/tmp` Directory**:  
   - Used by `gps-daemon.py` to store JSON data, updated every second.  
   - `gps-server.py` reads from the same JSON file to serve up-to-date info at `http://<device-ip>:8888`.

4. **Backup Config File**:  
   - In `arm/config_tema2.txt`, used to preserve the kernel config relevant to the Raspberry Pi 3B platform.

**The required DTB files** (`Device Tree Blob`) for `bcm2837-rpi-3-b` are generated using:

```bash
make dtbs
```

---

## 3. Custom Kernel ⚙️🐧

### 3.1. Kernel Source and Configuration

- A **v6.12 Linux kernel** was used, fetched from the official [Linux GitHub repository](https://github.com/torvalds/linux/), using a verified tag for that release.
- Main adjustments include:
  - Enabling the custom kernel option and disabling auto versioning (e.g., `-si-justin-marian.popescu`).
  - Specifying the location of the kernel tar.xz archive.
  - Including the SHA256 hash of the archive in **`linux.hash`** to ensure download integrity.
  - Detailed kernel configuration via **`linux-menuconfig`** to meet project needs—particularly **USB** and **FTDI FT232H** sensor support.

### 3.2. Additional Kernel Support

- **Serial Devices**: Enabled for communication with serial-based peripherals, essential for GPS data collection.
- **Character Devices**: General character device support.
- **Input Devices**: Activated for peripheral connectivity.
- **USB Support**:
  - **USB Networking (USBNET)**: Handles network connections over USB.
  - **FTDI USB Serial Converter**: Required for USB-connected GPS sensors.
  - **Driver FTDI for GPS**: Configured to handle NMEA data from the serial port.

### 3.3. Extended Functionality

Through kernel and system configurations, several extended features have been enabled:

- **Dynamic Device Management** with `udev`: Automatically detects and configures serial and USB interfaces.
- **Secure Remote Access** (SSH) with port forwarding via **OpenSSH** and **AutoSSH**.
- **DHCP Client** on `eth0` for automatic IP assignment.
- **Python/Flask** environment for hosting a lightweight web server to display GPS data.
- **IPv4/IPv6/TCP/Bluetooth** remain enabled by default for more robust connectivity, even if not directly used in this project.

---

## 4. Makefile and `launch-tema2.sh` – Structure and Paths 📜

After running:

```bash
make -j$(nproc)
```

The following files are produced in Buildroot:

- **DTB**: `../buildroot/output/build/linux-custom/arch/arm64/boot/dts/broadcom/`  
- **Kernel**: `../buildroot/output/build/linux-custom/arch/arm64/boot/`  
- **RootFS**: `../buildroot/output/images/`  

These paths are referenced in the project’s **Makefile** and in **`launch-tema2.sh`** to ensure correct deployment and boot.

### `launch-tema2.sh` Changes

- **Kernel**: Uses `vmlinuz-tema2` instead of `vmlinuz-test`:

```bash
KERNEL_FILE="vmlinuz-tema2"
```

**Console**: Switched from `console=ttyS0` to `console=ttyAMA0` for kernel compatibility:

```bash
_KERNEL_CONSOLE="console=ttyAMA0 console=ttyS1"
```

**Root Device**: Changed from `mmcblk0p2` to `mmcblk0` to match the generated SD card image:

```bash
ROOTDEV="mmcblk0"
```

---

## 5. Python Scripts 🐍

### 5.1. `gps-daemon.py`

- **Data Collection**: Reads raw NMEA data (e.g., `$GPGGA`, `$GPZDA`, `$GPGLL`) from the serial port via the `pyserial` library.  
- **Data Processing**: Converts NMEA coordinates to decimal format and UTC time to ISO 8601.  
- **JSON Output**: Writes processed GPS data to `/tmp/gps_data.json` (updated every second).  
- **Logging**: Writes logs and error messages to `/tmp/gps_daemon.log`.

### 5.2. `gps-server.py`

- **Flask Web Server**: Serves an interface displaying real-time GPS data.
- **API Endpoints**:  
  - `GET /api/gps`: Returns JSON with the latest GPS data.  
  - `GET /`: Serves `index.html`.
- **File Reading**: Pulls data from the JSON file generated by `gps-daemon.py`.  
- **Logging**: Writes logs to `/tmp/gps_server.log`.

### 5.3. `index.html`

- **User Interface**: Displays:
  - Latitude/Longitude, Altitude  
  - Number of satellites, GPS fix type  
  - Date/Time (UTC)  
  - An interactive map (Google Maps) for live location tracking  
- **Real-Time Updates**: Uses JavaScript to request `/api/gps` every 500 ms for fresh location info.

---

## 6. Additional Observations and Features 🔎

Below are some extra notes and features included in the project, derived from the extended documentation:

- **MD5-Encrypted Password**: The system uses `tema2` as the default password, encrypted in `/etc/passwd` and `/etc/shadow`.
- **AutoSSH**: Can maintain persistent SSH tunnels or port-forwards, which is helpful for remote management.
- **Udev Network Rules**: The custom file `mama_mea.rules` ensures that the primary network interface is always recognized as `eth0`, preventing name conflicts (e.g., `eth1`, `enxXXXX`, etc.).
- **Partitioning**: The final SD card image uses a single root partition (`mmcblk0`), making it simpler to reference in scripts (`ROOTDEV="mmcblk0"`).
- **Kernel Backup Config**: The file `config_tema2.txt` (in the `arm/` directory) serves as a snapshot of the kernel’s Buildroot configuration. It may also be partially auto-generated during the build process, ensuring that any specialized changes are documented.
