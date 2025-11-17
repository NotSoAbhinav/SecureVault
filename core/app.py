#!/usr/bin/env python3
import argparse
from core.orchestrator import Orchestrator

def main():
    parser = argparse.ArgumentParser(description="Secure File Vault CLI")
    sub = parser.add_subparsers(dest="cmd")

    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("--path", required=True, help="File or folder path to ingest")
    p_ingest.add_argument("--passphrase", required=True, help="Passphrase to derive key")

    p_restore = sub.add_parser("restore")
    p_restore.add_argument("--id", required=True, type=int, help="Vault ID to restore")
    p_restore.add_argument("--passphrase", required=True, help="Passphrase")
    p_restore.add_argument("--out", required=True, help="Output folder")

    args = parser.parse_args()
    orch = Orchestrator()

    if args.cmd == "ingest":
        orch.ingest_path(args.path, args.passphrase)
    elif args.cmd == "restore":
        orch.restore_id(args.id, args.passphrase, args.out)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
