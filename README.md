# 📐 Engineering CAD Suite: MBD Validator & Blueprint Generator

![Python](https://img.shields.io/badge/Python-3.10-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.56-red)
![License](https://img.shields.io/badge/License-MIT-green)

An automated, headless Model-Based Definition (MBD) validation tool built for precision engineering. This application bridges the gap between 3D mathematical geometry (STEP/IGES) and 2D derivative blueprints (PDF) to ensure manufacturing accuracy and automate Quality Assurance inspections.

## ✨ Key Features

* **🔍 Automated MBD Auditor:** Upload a 3D model and a 2D PDF drawing. The app extracts Key Control Characteristics (KCCs) directly from the 3D geometry and uses OCR to verify them against the blueprint.
* **📦 Universal Format Support:** Natively parses both `.STEP` and `.IGES` files using the open-source OpenCASCADE technology kernel—no expensive proprietary CAD licenses required.
* **🖍️ Visual Diagnostics Map:** Automatically generates a visual feature map, highlighting verified 3D dimensions in **Green** and unmatched/reference dimensions in **Red** directly on the PDF.
* **🖨️ Batch Blueprint Generator:** Upload multiple 3D models at once to automatically generate 2D orthographic projection PDFs (Front, Top, Isometric, etc.) with auto-calculated baseline dimensions.
* **🖥️ Native Desktop Feel:** Runs a local Streamlit server wrapped in a dark-mode, engineering-focused UI.

---

## 🚀 Quick Start Guide (Windows)

Follow these steps to get the suite running on your local machine. 

### 1. Prerequisites
You will need a Python environment manager installed on your machine. We recommend **[Miniconda](https://docs.anaconda.com/free/miniconda/index.html)** or Anaconda.

### 2. Installation
Clone this repository to your local machine:
```bash
git clone [https://github.com/YourUsername/Your-Repository-Name.git](https://github.com/YourUsername/Your-Repository-Name.git)
cd Your-Repository-Name
```

Next, build the required Python environment using the provided recipe. Open your Anaconda Prompt and run:
```bash
conda env create -f environment.yml
```

### 3. Launching the App
You do not need to use the command line ever again! Simply navigate to the folder in Windows Explorer and **double-click** the file:
> ⚙️ `Launch_App.bat`

This smart batch file will automatically locate your Anaconda installation, activate the environment, and spin up the dashboard in your default web browser.

---

## 🛠️ Built With

* **[OpenCASCADE (pythonocc-core)](https://github.com/tpaviot/pythonocc-core):** The core 3D modeling and mathematical kernel.
* **[PyMuPDF (fitz)](https://pymupdf.readthedocs.io/):** For high-speed PDF rasterization, text extraction, and bounding-box highlighting.
* **[Streamlit](https://streamlit.io/):** For the rapid, data-driven web interface.
* **[Matplotlib](https://matplotlib.org/):** For rendering 2D orthographic line projections.

---

## ⚖️ License & Legal

The core code of this repository is released under the **MIT License**. See the `LICENSE` file for details.

**⚠️ Commercial Usage Note:** 
Please note that this project depends on `PyMuPDF` (fitz), which is licensed under the **GNU AGPL v3.0**. If you plan to host this software on a public cloud server or integrate it into a closed-source commercial SaaS product, you must either comply with the AGPL terms (making your server code open-source) or acquire a commercial license from Artifex Software. For internal desktop use and portfolio demonstration, it is free to use.