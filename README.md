# cis-benchmark-parser
Python tool to extract and structure CIS Benchmark PDF controls into JSON
# CIS Benchmark PDF Parser

A Python tool to extract structured control details (Profile, Description, Rationale, Impact, Audit, Remediation, etc.) from CIS Benchmark PDFs and export them to JSON.

## Features
- Extracts full Table of Contents and control IDs
- Splits Appendix into per-control sections
- Parses control details with regex
- Exports structured JSON for easier automation
- Optimized with precompiled regex and multithreading

## Installation
```bash
git clone https://github.com/wijdentl-tlili/cis-benchmark-parser.git
cd cis-benchmark-parser
pip install -r requirements.txt
python cis_parser.py <Cis benchmark PDF file> <Output location>
