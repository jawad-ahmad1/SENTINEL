# Hardware Setup Guide — Sentinel RFID Attendance System

This guide covers everything you need to physically set up the Sentinel RFID Attendance System: what hardware to buy, how to connect it, how to configure kiosk terminals, and how to scale to multiple entrances.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Hardware Requirements](#hardware-requirements)
- [Deployment Architecture Options](#deployment-architecture-options)
- [Shopping Lists](#shopping-lists)
- [Setup Instructions](#setup-instructions)
- [Kiosk Mode Configuration](#kiosk-mode-configuration)
- [Multi-Entrance Setup](#multi-entrance-setup)
- [RFID Card Management](#rfid-card-management)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## How It Works

The Sentinel system uses the **simplest possible RFID integration** — USB keyboard emulation (HID mode). No custom drivers, no serial port configuration, no vendor SDK.

```
┌─────────────┐    USB HID     ┌──────────────┐    HTTP POST     ┌──────────────┐
│  RFID Card  │ ─── tap ────→  │  USB Reader  │ ── keystrokes ─→ │   Browser    │
│  (EM4100 /  │                │  (HID mode)  │                  │  (Kiosk UI)  │
│   MIFARE)   │                └──────────────┘                  └──────┬───────┘
└─────────────┘                                                         │
                                                                 POST /api/v1/scan
                                                                        │
                                                                 ┌──────▼───────┐
                                                                 │   Server     │
                                                                 │  (Docker)    │
                                                                 └──────────────┘
```

**What happens when an employee taps their card:**

1. Employee holds RFID card near the USB reader
2. Reader reads the card's UID and **types it as keyboard input** (e.g., `0012345678` + Enter)
3. The kiosk browser page captures this input via a hidden text field
4. JavaScript sends `POST /api/v1/scan {"uid": "0012345678"}` to the server
5. Server toggles IN/OUT, records attendance, and returns the employee's name
6. Kiosk displays "Welcome, John Smith — Clocked IN" with a success animation

> **Key insight:** The RFID reader behaves exactly like a USB keyboard. If you open Notepad and tap a card, you'll see the UID appear as typed text. That's all the reader does.

---

## Hardware Requirements

### 1. RFID Card Reader

Any USB RFID reader that operates in **HID keyboard-emulation mode** will work. The reader must:

- ✅ Connect via USB
- ✅ Output the card UID as keyboard keystrokes
- ✅ Send Enter/Return after the UID
- ✅ Work without installing proprietary drivers

**Recommended readers:**

| Reader | Frequency | Card Type | Price (INR) | Price (USD) | Best For |
|--------|-----------|-----------|-------------|-------------|----------|
| Generic EM4100 USB | 125 kHz | EM4100 / TK4100 | ₹300–₹600 | $5–$10 | Budget setups, small offices |
| ACR122U | 13.56 MHz | MIFARE Classic, NFC | ₹1,500–₹2,500 | $20–$35 | Higher security, NFC phones |
| RD200-LF | 125 kHz | EM4100 | ₹500–₹1,000 | $8–$15 | Indian market standard |
| HF-ICR | 13.56 MHz | MIFARE, DESFire | ₹2,000–₹4,000 | $25–$50 | Enterprise / card cloning prevention |

**Where to buy:**
- 🇮🇳 India: Amazon.in, Robu.in, Flipkart — search "USB RFID reader keyboard" or "USB RFID reader HID"
- 🌐 Global: Amazon, AliExpress, Adafruit, SparkFun

> [!TIP]
> **Start with the cheapest EM4100 USB reader** (~₹400 / ~$6). It works out of the box with no configuration. Upgrade to 13.56 MHz readers only if you need anti-cloning security.

### 2. RFID Cards / Tags

Buy cards that **match your reader's frequency**:

| Card Type | Frequency | Reader Compatibility | Price (per card) | Security Level |
|-----------|-----------|---------------------|-----------------|----------------|
| EM4100 / TK4100 | 125 kHz | EM4100 readers | ₹5–₹10 / $0.10–$0.30 | Basic (UID can be cloned) |
| MIFARE Classic 1K | 13.56 MHz | ACR122U, HF readers | ₹15–₹30 / $0.30–$0.60 | Medium |
| MIFARE DESFire EV2 | 13.56 MHz | HF readers | ₹50–₹100 / $1–$2 | High (anti-clone) |
| NFC Keychain Tags | 13.56 MHz | ACR122U, HF readers | ₹20–₹40 / $0.40–$0.80 | Medium (convenient form factor) |

**Recommended quantity:** Buy 20–30% more cards than your employee count (for replacements and new hires).

### 3. Kiosk Device (What Employees Tap Their Cards On)

The kiosk is simply **any device that runs a web browser and has a USB port**. Options:

| Device | Price (INR) | Price (USD) | Pros | Cons |
|--------|-------------|-------------|------|------|
| **Your existing PC/laptop** | ₹0 (free) | $0 | No extra cost | Must stay at entrance, can't move |
| **Old/refurbished laptop** | ₹0–₹5,000 | $0–$60 | Cheap, screen built in | Bulky |
| **Android tablet + OTG** | ₹8,000–₹15,000 | $100–$200 | Clean look, wall-mountable, touchscreen | Needs OTG adapter for USB reader |
| **Raspberry Pi 4/5** | ₹5,000–₹8,000 | $60–$100 | Tiny, low power, dedicated | Need separate monitor/screen |
| **Mini PC (Intel NUC, etc.)** | ₹10,000–₹25,000 | $120–$300 | Reliable, runs full OS | Need separate monitor |
| **All-in-one touchscreen PC** | ₹15,000–₹30,000 | $180–$400 | Professional look, everything built in | Most expensive |

### 4. Server (Where Docker Runs)

The server runs the backend (FastAPI + PostgreSQL + Redis + Nginx). Options:

| Option | Cost | Best For |
|--------|------|----------|
| **Same PC as kiosk** | ₹0 | Testing, small office (<20 employees) |
| **Dedicated PC/laptop** (always on) | ₹0–₹15,000 | Small–medium office, local network |
| **Cloud VPS** (DigitalOcean, AWS, Hostinger) | ₹300–₹800/month | Remote access, high availability |
| **On-premise server** | ₹20,000+ | Enterprise, data sovereignty requirements |

**Minimum server specs:** 2 CPU cores, 4 GB RAM, 20 GB SSD. Docker Compose handles all software.

---

## Deployment Architecture Options

### Option A: Single Machine — Everything on One Computer

```
┌─────────────────────────────────────────┐
│           YOUR LAPTOP / PC              │
│                                         │
│  ┌──────────┐   ┌───────────────────┐   │
│  │ Browser  │   │  Docker Compose   │   │
│  │ (Kiosk)  │   │  ┌─────┐ ┌─────┐ │   │
│  │          │──→│  │ App │ │ DB  │ │   │
│  └──────────┘   │  └─────┘ └─────┘ │   │
│                 └───────────────────┘   │
│  ┌──────────┐                           │
│  │ USB RFID │                           │
│  │ Reader   │                           │
│  └──────────┘                           │
└─────────────────────────────────────────┘
```

- **Cost:** ₹400–₹900 (just the reader + cards)
- **Good for:** Testing, personal projects, offices < 20 people
- **Drawback:** If the computer sleeps or shuts down, everything stops

### Option B: Separate Server + Kiosk Device (Recommended)

```
┌──────────────────────┐          ┌──────────────────────┐
│   SERVER (always on) │          │   KIOSK (entrance)   │
│                      │          │                      │
│   Docker Compose     │  network │   Browser pointed    │
│   ┌────┐ ┌────┐     │◄────────►│   to server IP       │
│   │App │ │ DB │     │          │                      │
│   └────┘ └────┘     │          │   USB RFID Reader    │
│   ┌────┐ ┌─────┐   │          │   plugged in here    │
│   │Redis│ │Nginx│   │          │                      │
│   └────┘ └─────┘   │          └──────────────────────┘
└──────────────────────┘
```

- **Cost:** ₹5,000–₹15,000 (reader + cards + kiosk device)
- **Good for:** Most offices, 20–500 employees
- **Advantage:** Server can be in a server room; kiosk stays at entrance

### Option C: Cloud Server + Multiple Kiosks (Enterprise)

```
                    ┌───────────────────┐
                    │   CLOUD SERVER    │
                    │   (VPS / AWS)     │
                    │   Docker Compose  │
                    └─────────┬─────────┘
                              │ HTTPS
              ┌───────────────┼───────────────┐
              │               │               │
     ┌────────▼──────┐ ┌─────▼────────┐ ┌────▼─────────┐
     │ KIOSK 1       │ │ KIOSK 2      │ │ KIOSK 3      │
     │ Main Entrance │ │ Back Door    │ │ Parking Gate │
     │ Tablet+Reader │ │ Tablet+Reader│ │ Tablet+Reader│
     └───────────────┘ └──────────────┘ └──────────────┘
```

- **Cost:** ₹300–₹800/month (VPS) + ₹9,000 per kiosk (tablet + reader)
- **Good for:** Multi-location, remote management, enterprise
- **Advantage:** Accessible from anywhere, automatic backups, high uptime

---

## Shopping Lists

### Budget Setup (< ₹1,000 / < $15) — Use Your Existing Computer

| # | Item | Qty | Unit Price | Total |
|---|------|-----|-----------|-------|
| 1 | EM4100 USB RFID Reader (HID) | 1 | ₹400 | ₹400 |
| 2 | EM4100 RFID Cards (pack of 25) | 1 | ₹200 | ₹200 |
| | | | **Total** | **₹600** |

### Standard Setup (~ ₹10,000 / ~$120) — Dedicated Kiosk

| # | Item | Qty | Unit Price | Total |
|---|------|-----|-----------|-------|
| 1 | EM4100 USB RFID Reader (HID) | 1 | ₹500 | ₹500 |
| 2 | EM4100 RFID Cards (pack of 100) | 1 | ₹700 | ₹700 |
| 3 | Android Tablet (10", any brand) | 1 | ₹8,000 | ₹8,000 |
| 4 | USB OTG Adapter (USB-C to USB-A) | 1 | ₹150 | ₹150 |
| 5 | Tablet Wall Mount | 1 | ₹500 | ₹500 |
| | | | **Total** | **₹9,850** |

### Enterprise Setup (~ ₹35,000 / ~$420) — Multiple Entrances

| # | Item | Qty | Unit Price | Total |
|---|------|-----|-----------|-------|
| 1 | ACR122U USB NFC Reader | 3 | ₹2,000 | ₹6,000 |
| 2 | MIFARE Classic 1K Cards (pack of 200) | 1 | ₹4,000 | ₹4,000 |
| 3 | Android Tablets (10") | 3 | ₹8,000 | ₹24,000 |
| 4 | USB OTG Adapters | 3 | ₹150 | ₹450 |
| 5 | Tablet Wall Mounts | 3 | ₹500 | ₹1,500 |
| 6 | Cloud VPS (monthly) | 1 | ₹500/mo | ₹500/mo |
| | | | **Total (one-time)** | **₹35,950** |

---

## Setup Instructions

### Step 1: Verify the RFID Reader Works

1. **Plug the USB RFID reader** into any computer (no driver installation needed)
2. **Open a text editor** (Notepad on Windows, TextEdit on Mac, gedit on Linux)
3. **Click inside the text editor** so it has keyboard focus
4. **Tap an RFID card** on the reader
5. **Expected result:** A string of characters appears in the text editor, followed by a newline

```
Example output in Notepad:
0012345678
```

If you see text appear → **the reader works correctly** ✅

> [!WARNING]
> If nothing appears when you tap a card:
> - Make sure the reader's LED is on (indicating power)
> - Try a different USB port
> - Make sure you're tapping a compatible card (125 kHz card with 125 kHz reader)
> - On Linux, check `dmesg | tail` for USB device detection

### Step 2: Start the Server

Follow the [Deployment Guide](DEPLOYMENT_GUIDE.md) to start Docker Compose. In summary:

```bash
# Clone the project
git clone https://github.com/yourcompany/sentinel-attendance.git
cd sentinel-attendance

# Configure environment
cp .env.example .env
nano .env   # fill in your production values

# Start all services
docker compose up -d --build

# Verify
docker compose ps              # all containers should be "healthy"
curl http://localhost/api/v1/health   # should return {"db": true, "redis": true}
```

### Step 3: Open the Kiosk Page

On the kiosk device (the computer/tablet at the entrance):

1. **Open a web browser** (Chrome recommended)
2. **Navigate to the server's address:**
   - Same machine: `http://localhost`
   - Local network: `http://192.168.1.XXX` (your server's IP)
   - Cloud / domain: `https://attendance.company.com`
3. The **kiosk page** loads with a scan ring animation and live clock

### Step 4: Test a Card Scan

1. **Make sure the browser tab is in focus** (click on it)
2. **Tap an RFID card** on the USB reader
3. **Expected:** The kiosk shows:
   - "Welcome, Employee-0012345678" (auto-registered with the card UID)
   - Event: **IN**
   - A success animation plays
4. **Tap the same card again:**
   - Event toggles to **OUT**
5. **Check the admin panel** at `/admin.html` to verify the attendance record appears

### Step 5: Register Employees with Their Cards

1. Navigate to `/register.html` (or the admin panel)
2. Enter the employee's name, department, and position
3. For the RFID UID field — either:
   - Type the UID manually (the number you saw in Notepad during Step 1)
   - Or tap "Scan Card" and hold the card near the reader
4. Submit → The employee is now linked to that card
5. Next time they scan, the kiosk will show their **real name** instead of "Employee-XXXX"

---

## Kiosk Mode Configuration

To prevent employees from accidentally closing the browser or navigating away:

### Chrome Kiosk Mode (Windows)

Create a shortcut with this target:

```
"C:\Program Files\Google\Chrome\Application\chrome.exe" --kiosk --app=http://192.168.1.100
```

This opens Chrome in full-screen with no address bar, tabs, or navigation controls.

### Chrome Kiosk Mode (Linux / Raspberry Pi)

```bash
# Install Chromium
sudo apt install -y chromium-browser

# Launch in kiosk mode
chromium-browser --kiosk --disable-infobars --no-first-run http://192.168.1.100
```

**Auto-start on boot (Raspberry Pi):**

```bash
nano ~/.config/lxsession/LXDE-pi/autostart

# Add this line:
@chromium-browser --kiosk --disable-infobars --no-first-run http://192.168.1.100
```

### Android Tablet Kiosk Mode

**Option A: Chrome Kiosk (free)**
1. Open Chrome → Navigate to your server URL
2. Tap ⋮ Menu → "Add to Home screen"
3. Open the shortcut (launches as full-screen web app)
4. Enable Android's "Screen Pinning" (Settings → Security → Screen Pinning)

**Option B: Fully Kiosk Browser (₹700 / $8 one-time)**
1. Install [Fully Kiosk Browser](https://www.fully-kiosk.com/) from Play Store
2. Set the URL to your server address
3. Enable kiosk mode — locks the tablet to only show your attendance page
4. Prevents access to settings, home button, and other apps

### Windows Assigned Access (Dedicated Kiosk PC)

Windows 10/11 has a built-in kiosk mode:

1. Settings → Accounts → Family & other users → Set up a kiosk
2. Create a kiosk account
3. Choose Microsoft Edge as the kiosk app
4. Set the URL to your server address
5. The PC will boot directly into the attendance page

---

## Multi-Entrance Setup

To place kiosks at multiple doors/entrances, you just need **one reader + one device per entrance**, all pointing to the same server:

```
Server (one instance, running Docker):
  http://192.168.1.100

Kiosk 1 (Main Entrance):
  Tablet browser → http://192.168.1.100
  USB Reader plugged in via OTG

Kiosk 2 (Back Door):
  Old laptop browser → http://192.168.1.100
  USB Reader plugged in via USB

Kiosk 3 (Parking Gate):
  Raspberry Pi browser → http://192.168.1.100
  USB Reader plugged in via USB
```

All kiosks share the same server, database, and employee records. An employee can scan at **any entrance** and the system records it identically.

> [!NOTE]
> The current system does not track **which entrance** the scan came from. If you need
> location tracking per reader, a custom `location` field can be added to the scan request
> in a future update.

---

## RFID Card Management

### Assigning a New Card

1. Login to the admin panel (`/login.html`)
2. Go to Employee Registration (`/register.html`)
3. Fill in employee details + scan/enter the RFID UID
4. Submit →Done

### Replacing a Lost Card

1. Login to the admin panel
2. Go to Employee Management (`/employees.html`)
3. Find the employee → Click Edit
4. Update the `rfid_uid` field with the new card's UID
5. Save → The old card stops working, new card is active

### Deactivating an Employee

1. Go to Employee Management
2. Find the employee → Click Delete
3. This performs a **soft-delete** (sets `is_active = false`)
4. The employee's card will be rejected with "Employee account is deactivated"
5. All historical attendance records are preserved

### Card UID Format

The system accepts UIDs matching this pattern: `A-Za-z0-9:_-` (2 to 64 characters).

Common UID formats from different readers:
- EM4100: `0012345678` (10-digit decimal)
- MIFARE: `A1B2C3D4` (8-character hex)
- Some readers: `01:23:45:67` (colon-separated hex)

All formats are accepted as long as they use only alphanumeric characters, colons, underscores, or hyphens.

---

## Troubleshooting

### Reader Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Nothing happens when card is tapped | Browser not focused | Click on the kiosk page, then tap again |
| UID appears in browser URL bar | Reader is too fast, browser interprets as URL | Ensure the hidden input field on the kiosk page has focus |
| Reader LED doesn't light up | No USB power | Try a different USB port; try a powered USB hub |
| UID appears in Notepad but not in kiosk | Wrong browser tab is active | Switch to the kiosk tab and click on it |
| Card works on one reader but not another | Frequency mismatch | Ensure card frequency (125 kHz or 13.56 MHz) matches the reader |
| Double scan / bouncing | Card held too long | The system has anti-bounce protection (`BOUNCE_WINDOW_SECONDS=2`); just tap and remove |

### Kiosk Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| "Failed to connect" on kiosk page | Server not running or unreachable | Check `docker compose ps`; check network/firewall |
| Page loads but scan doesn't register | JavaScript error | Open browser DevTools (F12) → Console tab → check for errors |
| Tablet screen turns off | Power saving | Disable auto-sleep in tablet settings; keep charger connected |
| Chrome exits kiosk mode | User pressed F11 or Alt+F4 | Use OS-level kiosk mode (Windows Assigned Access, Android Screen Pinning) |

### Network Issues

| Problem | Cause | Solution |
|---------|-------|----------|
| Kiosk can't reach server | Different network/subnet | Ensure both are on the same network; check with `ping <server-ip>` |
| Scans work on `localhost` but not from tablet | Firewall blocking port 80/443 | Open the port: `sudo ufw allow 80/tcp` |
| HTTPS certificate warning on kiosk | Self-signed or misconfigured cert | Use Let's Encrypt for valid certificates |

---

## FAQ

**Q: Do I need a separate laptop for the kiosk?**  
A: No. You can run the server and the kiosk browser on the same computer. However, for a professional setup, a dedicated device (tablet, old laptop, or Raspberry Pi) at the entrance is recommended so the server can run elsewhere.

**Q: Can I use my phone's NFC as a card?**  
A: Only if you use a 13.56 MHz reader (like ACR122U) and your phone supports NFC host card emulation (HCE). Most Android phones support this. iPhones do not support HCE for third-party apps.

**Q: How far does the card need to be from the reader?**  
A: Typical range is 1–5 cm (0.5–2 inches). The employee just needs to tap or hold the card near the reader for a fraction of a second.

**Q: Can employees share cards?**  
A: Technically yes — the system tracks card UIDs, not biometrics. If buddy-punching is a concern, consider adding a camera at the kiosk or using biometric readers in a future upgrade.

**Q: What happens if the internet goes down?**  
A: If the server runs locally (Option A or B), the system works without internet. If using a cloud server (Option C), kiosks need internet connectivity to reach the server.

**Q: How many employees can the system handle?**  
A: The system has been load-tested and can handle hundreds of scans per minute. PostgreSQL and the indexed queries scale to thousands of employees without performance issues.

**Q: Can I use a barcode scanner instead of RFID?**  
A: Yes! Any USB HID barcode scanner that outputs text + Enter will work identically. Print barcodes on employee ID cards instead of using RFID chips.

**Q: What if the power goes out?**  
A: Attendance data is stored in PostgreSQL with a persistent Docker volume. When power returns and Docker starts, all data is intact. Consider a UPS (uninterruptible power supply) for the server to prevent database corruption during unexpected shutdowns.

---

## Summary

| Component | What You Need | Minimum Cost |
|-----------|--------------|-------------|
| RFID Reader | Any USB HID reader (EM4100 recommended to start) | ₹400 |
| RFID Cards | Match your reader's frequency, buy 20% extra | ₹200 (25 cards) |
| Kiosk Device | Any device with a browser + USB port | ₹0 (existing PC) |
| Server | Any computer that can run Docker, or a cloud VPS | ₹0 (existing PC) |
| **Minimum total** | **Reader + Cards** | **₹600 (~$8)** |

The entire hardware setup takes **under 30 minutes**: plug in the reader, start Docker, open the browser, and tap a card.
