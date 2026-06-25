# scheduler-ORB

A scheduler implementation with synthetic data generation for testing and evaluation.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Running the Scheduler](#running-the-scheduler)

## Prerequisites

### Install `uv`

Follow the official installation guide:

https://docs.astral.sh/uv/getting-started/installation/

### Install Python 3.14

```bash
uv python install 3.14
```

## Environment Setup

### Create a virtual environment

```bash
uv venv --python 3.14
```

### Activate the virtual environment

#### macOS / Linux

```bash
source .venv/bin/activate
```

#### Windows (PowerShell)

```powershell
.venv\Scripts\Activate.ps1
```

### Install dependencies

```bash
uv pip install -r requirements.txt
```

## Running the Scheduler

### 1. Generate synthetic data

```bash
python synthesize_data.py
```

### 2. Run the scheduler

```bash
python scheduler.py
```