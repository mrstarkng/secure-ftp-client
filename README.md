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
- [Troubleshooting](#troubleshooting)
- [Contribution Guidelines](#contribution-guidelines)

---

## Project Overview

This project is a multi-session, secure FTP client featuring a Python/PyQt6 graphical interface and a high-performance C++ backend. The backend handles all FTP protocol logic and file scanning via a ClamAV agent. The two layers communicate using `pybind11`.

---

## Project Structure

```
FTPClient/
│   CMakeLists.txt                # CMake build configuration
│   Readme.md                     # Project documentation
│   requirements.txt              # Python dependencies
│   
├───build/                        # CMake build output directory
│   │   ftp_engine.pyd            # Generated Python module
│   │   CMakeCache.txt
│   │   Makefile
│   │   
│   └───CMakeFiles/               # CMake internal files
│       └───...                   # (build artifacts)
│
├───frontend/                     # Python frontend application
│   │   main.py                   # Application entry point
│   │   session_manager.py        # Session management logic
│   │   cli_widget.py             # Command-line interface widget
│   │   gui_widget.py             # Graphical user interface widget
│   │   libgcc_s_seh-1.dll        # Required DLL dependencies
│   │   libstdc++-6.dll
│   │   libwinpthread-1.dll
│   │   
│   └───__pycache__/              # Python bytecode cache
│       └───...                   # (compiled Python files)
│
└───src/                          # C++ source code
    ├───client/                   # Client-side code
    │   └───binder.cpp            # Pybind11 bindings
    │
    ├───common/                   # Shared utilities and constants
    │   ├───constants.h
    │   ├───socket_utils.h
    │   └───socket_utils.cpp
    │
    ├───connectors/               # External service connectors
    │   ├───clamav_connector.h
    │   └───clamav_connector.cpp  # ClamAV integration
    │
    └───core/                     # Core FTP functionality
        ├───command_handler.h
        ├───command_handler.cpp   # FTP command processing
        ├───ftp_connection.cpp    # Connection management
        ├───ftp_controller.h      # Main FTP controller
        ├───ftp_directory_ops.cpp # Directory operations
        └───ftp_file_ops.cpp      # File operations
```

> 💡 **Note:** The Python frontend files are located in the `frontend/` directory, and the compiled `.pyd` module is generated in the `build/` directory. Additional files and directories may be added during development.

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

The project includes a `requirements.txt` file in the root directory with all necessary Python dependencies:

```txt
PyQt6>=6.4.0
pybind11>=2.10.0
```

Install the dependencies using:

```bash
pip install -r requirements.txt
```

**Package Details:**
- **PyQt6**: GUI framework for the frontend application
- **pybind11**: C++/Python binding library for interfacing with the backend

---

## Building the C++ Backend (`ftp_engine.pyd`)

The backend must be compiled into a Python-compatible module (`.pyd`) using CMake. The output will be generated in the `build/` directory.

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
cd /path/to/project

# Create and enter build directory
mkdir -p build
cd build

# Clean previous build (optional)
rm -rf *

# Run CMake (replace with your Python path)
cmake .. -G "MinGW Makefiles" -DPython_EXECUTABLE="/path/to/anaconda3/envs/ftp_client_dev/python.exe"

# Build the project
cmake --build . --config Release
```

You should get a file `ftp_engine.pyd` in the `build/` folder.

---

## Handling DLL Dependencies

The required DLL files are already located in the `frontend/` directory:

- `libgcc_s_seh-1.dll`
- `libstdc++-6.dll`
- `libwinpthread-1.dll`

These DLLs are copied from `C:\msys64\ucrt64\bin` and are necessary for the C++ backend to work properly.

**Current directory structure:**
- `frontend/main.py` - Application entry point
- `frontend/*.dll` - Required DLL dependencies
- `build/ftp_engine.pyd` - Generated Python module

---

## Running the Application

1. Ensure your Conda environment is active:
   ```bash
   conda activate ftp_client_dev
   ```

2. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

3. Update the Python path to include the build directory. Add this to the beginning of `main.py`:
   ```python
   import sys
   import os
   
   # Add the build directory to Python path
   build_dir = os.path.join(os.path.dirname(__file__), '..', 'build')
   if os.path.exists(build_dir):
       sys.path.insert(0, build_dir)
   ```

4. Run the application:
   ```bash
   python main.py
   ```

---

## Troubleshooting

### Common Issues:

1. **ImportError: No module named 'ftp_engine'**
   - Ensure the `ftp_engine.pyd` file is in the `build/` directory
   - Verify the Python path is correctly set in `main.py`

2. **DLL Load Failed**
   - Ensure all required DLLs are in the `frontend/` directory
   - Check that the DLLs are the correct architecture (x64)

3. **PyQt6 Import Error**
   - Ensure you've installed the requirements: `pip install -r requirements.txt`
   - Verify you're using the correct Conda environment

---

## Contribution Guidelines

Please refer to **[CONTRIBUTING.md](CONTRIBUTING.md)** for our Git workflow, branch naming conventions, commit format, and pull request guidelines.

---

## Development Notes

- **Python Version**: 3.12 (specified in Conda environment)
- **C++ Standard**: C++20
- **Build System**: CMake with MinGW-w64 UCRT
- **GUI Framework**: PyQt6
- **Last Updated**: 2025-07-03 01:43:29 UTC by Kostovite
