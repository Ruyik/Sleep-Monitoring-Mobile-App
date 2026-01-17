# Sleep-Monitoring-Mobile-App
IoT-Driven Environmental Assessment and Automation System for Optimized Sleep

Project Overview

This project, developed for the SEEL 4723 Project Capstone (Group E1G08), is an integrated IoT solution designed to improve sleep quality and respiratory health. The system addresses unregulated bedroom environments (high temperature/poor air quality) and behavioral inconsistencies (bedtime procrastination) through real-time environmental regulation and automated behavioral reinforcement.

System Architecture & Technical Stack

The system employs a multi-layered architecture to bridge the gap between physical sensors and user interaction:

Hardware Layer: Powered by an ESP32 Microcontroller interfaced with LM35 (Temperature) and MQ135 (Air Quality) sensors. Actuation is handled via an L298N Motor Driver controlling a PWM Exhaust Fan and a DC Room Fan.

IoT Middleware: Node-RED serves as the orchestration layer, processing MQTT payloads, evaluating thresholds, and providing a diagnostic dashboard.

Application Layer: A mobile application built using Python and the Kivy framework, providing a high-performance Human-Machine Interface (HMI).

Cloud & Data: Integrated Google Cloud Services for authentication and TinyDB for localized data persistence.

Core Software Features

Smart Health Dashboard: Real-time visualization of room metrics via intuitive gauges, providing immediate awareness of sleep-disrupting factors.

Personalized Sleep Scheduling: Features interactive goal setting with Dynamic Extension Logic to track and penalize bedtime deviations.

Automated IoT Light Control: Triggers an MQTT "OFF" command upon countdown expiration to enforce a disciplined sleep transition.

Sleep Consistency Analytics: Uses a penalty-based formula ($100\% - \text{Penalty}$) to track historical sleep hygiene over a 7-day bar chart.

Companion Ecosystem:

Virtual Sleep Pet: A gamified reinforcement tool where the pet's health mirrors the user's sleep consistency.

Sleep Assistant Bot: A decision-tree-based support tool to identify and solve barriers to sleep (digital addiction, anxiety, etc.).

Key Files in this Repository

main.py: The central Python orchestrator. It manages screen transitions, initializes background services, and implements asynchronous threading to ensure the UI remains responsive during network operations.

buildozer.spec: The configuration file required for packaging the Python application into an Android APK. It defines all requirements (e.g., kivy, paho-mqtt, tinydb) and Android permissions (INTERNET, NETWORK_STATE).

backend/: Contains the modular service logic for MQTT clients, database management, and pet/bot interactions.

UI/: Contains .kv files defining the high-contrast, professional layout of the mobile interface.

Deployment & Testing

Local Testing (Windows/Linux/Mac)

Install Python dependencies: pip install kivy paho-mqtt tinydb

Ensure your MQTT Broker (Node-RED) is active and the ESP32 is online.

Execute: python main.py

Mobile Packaging (Android)

To compile the project into a mobile application:

Set up a Linux environment (Ubuntu or WSL).

Install Buildozer and its dependencies.

Run: buildozer -v android debug

The generated .apk file will be found in the bin/ directory.

Development Challenges & Solutions

APK Stability: Addressed MQTT connectivity issues during Android deployment by implementing a background reconnection thread and optimizing socket management.

Security: Managed sensitive service account credentials through GitHub's Push Protection protocols and localized .gitignore configurations.

Asynchronous Logic: Utilized Python's threading and Kivy's Clock to prevent UI freezes during hardware communication.

Project Team (Group E1G08)

Supervisor: Dr. Jamaluddin bin Zakaria

Members: Muhamad Luqman Bin Muhamad Nor, Muhamad Aqil Bin A Halid, Lim Jun Ning, Ng Ru Yik
