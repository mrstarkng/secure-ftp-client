# Secure FTP Client – Developer's Guide

Welcome to the team! This document provides all the necessary steps to set up your development environment, build the C++ backend, and run the application.

> ⚠️ **This guide is for developers only.**

---

## Table of Contents

- [Project Overview](#project-overview)
- [Project Structure](#project-structure)
- [Core Technologies](#core-technologies)
- [Environment Setup (Step-by-Step)](#environment-setup-step-by-step)
  - [Step 1: Prerequisites](#step-1-prerequisites)
  - [Step 2: Clone the Repository](#step-2-clone-the-repository)
  - [Step 3: Set Up Conda Environment](#step-3-set-up-conda-environment)
  - [Step 4: Install Python Dependencies](#step-4-install-python-dependencies)
- [Building the C++ Backend (`ftp_engine.pyd`)](#building-the-c-backend-ftp_enginepyd)
  - [Finding Your Python Executable Path](#finding-your-python-executable-path)
  - [Running CMake and Build](#running-cmake-and-build)
- [Handling DLL Dependencies](#handling-dll-dependencies)
- [Running the Application](#running-the-application)
- [Contribution Guidelines](#contribution-guidelines)

---

## Project Overview

This project is a multi-session, secure FTP client featuring a Python/PyQt6 graphical interface and a high-performance C++ backend. The backend handles all FTP protocol logic and file scanning via a ClamAV agent. The two layers communicate using `pybind11`.

---

## Project Structure

```
.
├── build/                # CMake build directory
├── common/               # Shared C++ code (constants, exceptions)
├── connectors/           # C++ connectors (ClamAV)
├── core/                 # Core C++ FTP logic
├── python_ui/            # Python source files
│   ├── main.py           # Application entry point
│   ├── cli_widget.py
│   ├── gui_widget.py
│   └── session_manager.py
├── binder.cpp            # Pybind11 bindings
├── CMakeLists.txt        # CMake build script
└── requirements.txt      # Python dependencies
```

> 💡 **Note:** All Python files are expected to be located in the `python_ui/` directory. If not already moved, please do so before continuing.

---

## Core Technologies

- **Frontend**: Python 3.12 with PyQt6
- **Backend**: C++20
- **Binding**: pybind11
- **Build System**: CMake + MinGW-w64 (UCRT)
- **Environment**: Conda

---

## Environment Setup (Step-by-Step)

### Step 1: Prerequisites

Install the following tools:

1. **Git** – Version control  
2. **Anaconda / Miniconda** – Python environment manager  
3. **MSYS2** – For MinGW-w64 C++ compilation  
   - Download from [https://www.msys2.org](https://www.msys2.org)
   - Launch the **MSYS2 UCRT64** terminal and run:

     ```bash
     pacman -Syu   # First update
     ```

   - Then install required packages:

     ```bash
     pacman -S --needed git mingw-w64-ucrt-x86_64-toolchain mingw-w64-ucrt-x86_64-cmake
     ```

---

### Step 2: Clone the Repository

```bash
git clone <your-repository-url>
cd <repository-folder>
```

---

### Step 3: Set Up Conda Environment

Create and activate a new Conda environment:

```bash
conda create -n ftp_client_dev python=3.12
conda activate ftp_client_dev
```

---

### Step 4: Install Python Dependencies

Create a `requirements.txt` file in the root folder:

```
PyQt6
pybind11
```

Install them using:

```bash
pip install -r requirements.txt
```

---

## Building the C++ Backend (`ftp_engine.pyd`)

The backend must be compiled into a Python-compatible module (`.pyd`) using CMake.

---

### Finding Your Python Executable Path

CMake requires the full path to the Python interpreter inside your Conda environment.

1. Ensure the `ftp_client_dev` environment is activated.
2. Run the following (PowerShell):

```powershell
(Get-Command python).Source
```

Or (Cmd / PowerShell):

```cmd
where python
```

Copy the Python path located inside `anaconda3/envs/ftp_client_dev`.

---

### Running CMake and Build

> 🔧 Run the following **from MSYS2 UCRT64 terminal**.

```bash
# Navigate to your project directory
cd /d/path/to/project

# Create and enter build directory
mkdir -p build
cd build

# Clean previous build (optional)
rm -rf *

# Run CMake (replace with your Python path)
cmake .. -G "MinGW Makefiles" -DPython_EXECUTABLE="D:/path/to/python.exe"

# Build the project
cmake --build . --config Release
```

You should get a file like `ftp_engine.cp312-win_amd64.pyd` in the `build/` folder.

---

## Handling DLL Dependencies

Copy the following DLLs from `C:\msys64\ucrt64\bin` to your **project root directory** (next to `main.py`):

- `libgcc_s_seh-1.dll`
- `libstdc++-6.dll`
- `libwinpthread-1.dll`

Also copy the generated `.pyd` file from the `build/` folder to the root.

**Final root directory should contain:**

- `main.py`
- `ftp_engine.cp312-win_amd64.pyd`
- Required DLLs
- Other Python and project files

---

## Running the Application

Ensure your Conda environment is active, then:

```bash
python main.py
```

---

## Contribution Guidelines

Please refer to **[CONTRIBUTING.md](CONTRIBUTING.md)** for our Git workflow, branch naming conventions, commit format, and pull request guidelines.
