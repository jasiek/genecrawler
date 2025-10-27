#!/usr/bin/env python3
"""
GeneCrawler - Heredis Database to Genealogical Database Query Tool

This script reads a Heredis genealogy database and queries multiple Polish genealogical
databases for information about each person in the database:
- Geneteka (geneteka.genealodzy.pl)
- PTG PomGenBaza (www.ptg.gda.pl)
- Poznan Project (poznan-project.psnc.pl)
- BaSIA (www.basia.famula.pl)

This is the main entry point that delegates to the genecrawler package.
"""

from genecrawler.cli import main

if __name__ == "__main__":
    main()
