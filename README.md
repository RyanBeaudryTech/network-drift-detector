# Network Drift Detector

This project is a Python-based network automation tool designed to detect configuration and state drift across network devices by comparing structured snapshots over time.

Instead of relying on raw CLI text diffs, this tool parses command output into structured data and highlights meaningful changes to interfaces, routing, and ARP tables.

This project was built and tested using a network lab environment and is intended as a portfolio project demonstrating real-world network automation and operational thinking.

---

## Overview

Network devices change frequently due to maintenance, automation, or human error. This tool helps identify unintended or unexpected changes by:

- Comparing the two most recent snapshots per device
- Detecting logical configuration and state drift
- Classifying changes by severity
- Presenting results in a clean, human-readable format

---

## Features

- Snapshot-based comparison per device
- Structured diffs instead of raw text comparison
- Supports:
  - Interfaces
  - Routing table
  - ARP table
- Severity classification:
  - HIGH (interface state changes)
  - MEDIUM (routing changes)
  - LOW (ARP changes)
- Collapsed interface events (admin and operational state shown together)
- Ignore rules to suppress expected or noisy changes
- Diff results saved for auditing and review

---

## Project Structure

- snapshots/  
  - Per-device snapshot history stored as JSON  
- diffs/  
  - Saved drift results per device  
- diff_engine/  
  - drift_detector_v2.py  
  - diff_utils_v2.py  
  - ignore_rules.json  
- README.md  

---

## How It Works

1. **Snapshots are collected**  
   Device command output is stored as JSON snapshots, including routing tables, ARP tables, and interface state.

2. **Data is normalized**  
   Raw CLI output is parsed into structured dictionaries so changes are compared logically instead of line by line.

3. **Structured diffs are generated**  
   Changes are identified as added, removed, or modified.

4. **Severity is classified**  
   - Interface state changes are HIGH severity  
   - Routing changes are MEDIUM severity  
   - ARP changes are LOW severity  

5. **Results are displayed**  
   Output is grouped by severity and section, with interface changes collapsed into a single readable event.

---

## Example Output

Drift Detected

[HIGH]

Interfaces  
- GigabitEthernet0/1: admin down -> up, oper down -> up

[MEDIUM]

Routing  
- C 10.3.7.0/24 is directly connected, GigabitEthernet0/1  
- L 10.3.7.1/32 is directly connected, GigabitEthernet0/1  

[LOW]

ARP  
- ARP 5254.0014.3185 on GigabitEthernet0/1  

---

## Testing in a Lab Environment

Recommended test scenarios:

- Shut and no shut an interface
- Add or remove a static route
- Clear ARP entries
- Change interface IP addressing
- Introduce known changes and suppress them using ignore rules

---

## Configuration

### Ignore Rules

Expected or noisy changes can be filtered using `ignore_rules.json`.  
Rules allow you to ignore specific paths or entire sections to reduce false positives.

---

## Design Goals

- Prefer structured data over raw text parsing
- Reduce noise while highlighting meaningful change
- Produce output that is easy to scan during incidents
- Reflect real-world network operations workflows

---

## Possible Future Enhancements

- Snapshot collection via SSH using Netmiko or Paramiko
- Support for additional protocols such as BGP and OSPF
- Export results as JSON, Markdown, or HTML
- Exit codes for CI or monitoring integration
- Historical drift trend analysis

---

## Disclaimer

This project was built for learning and portfolio purposes and is not intended to replace enterprise configuration management systems.
