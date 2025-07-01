# Hands-on Scoring System

This repository contains a lightweight scoring system designed for hands-on labs and workshops.

It consists of two components:

- `server/`: A Python server that receives scoring submissions, stores results, and sends custom metrics to Datadog.
- `client/`: A CLI tool that users run inside lab environments (e.g., Instruqt) to register, submit missions, and track their progress.