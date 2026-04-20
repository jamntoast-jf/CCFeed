#!/usr/bin/env python3
"""
One-time migration: import all records from an ATProto PDS collection into
the CCFeed SQLite database.

Usage:
    python tools/migrate_from_pds.py \
        --db ~/data/LabNoteFeed/notes.db \
        --pds-url https://jamntoast.com \
        --handle jamntoast.jamntoast.com \
        --password <app-password> \
        --collection com.labnote.note

Safe to re-run: uses INSERT OR IGNORE so duplicates are skipped.
"""

import argparse
import sys
import os

import urllib.request
import urllib.error
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.db import init_db, insert_note


def _post_json(url, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def _get_json(url, headers=None, params=None):
    if params:
        qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url = f"{url}?{qs}"
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


import urllib.parse


def create_session(pds_url, handle, password):
    return _post_json(
        f"{pds_url}/xrpc/com.atproto.server.createSession",
        {"identifier": handle, "password": password},
    )


def fetch_all_records(pds_url, did, collection, access_jwt):
    headers = {"Authorization": f"Bearer {access_jwt}"}
    records = []
    cursor = None

    while True:
        params = {"repo": did, "collection": collection, "limit": "100"}
        if cursor:
            params["cursor"] = cursor

        data = _get_json(
            f"{pds_url}/xrpc/com.atproto.repo.listRecords",
            headers=headers,
            params=params,
        )
        batch = data.get("records", [])
        records.extend(batch)

        cursor = data.get("cursor")
        if not cursor or not batch:
            break

    return records


def main():
    parser = argparse.ArgumentParser(description="Migrate ATProto PDS collection to CCFeed SQLite DB")
    parser.add_argument("--db", required=True, help="Path to SQLite DB file")
    parser.add_argument("--pds-url", required=True)
    parser.add_argument("--handle", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--collection", default="com.labnote.note")
    args = parser.parse_args()

    db_path = os.path.expanduser(args.db)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    print(f"Initialising DB at {db_path} ...")
    init_db(db_path)

    print(f"Authenticating to {args.pds_url} as {args.handle} ...")
    session = create_session(args.pds_url, args.handle, args.password)
    did = session["did"]
    jwt = session["accessJwt"]

    print(f"Fetching records from {args.collection} (DID: {did}) ...")
    records = fetch_all_records(args.pds_url, did, args.collection, jwt)
    print(f"Fetched {len(records)} records from PDS.")

    imported = 0
    skipped = 0
    for r in records:
        val = r.get("value", {})
        rkey = r["uri"].split("/")[-1]
        text = val.get("text", "")
        service = val.get("service", "claude-code")

        raw_tags = val.get("tags", "")
        if isinstance(raw_tags, list):
            tags = ",".join(raw_tags)
        else:
            tags = str(raw_tags)

        created_at = val.get("createdAt", "")

        row_id = insert_note(db_path, rkey=rkey, text=text, service=service,
                             tags=tags, created_at=created_at)
        if row_id:
            imported += 1
        else:
            skipped += 1

    print(f"Done. Imported: {imported}, Skipped (duplicates): {skipped}")


if __name__ == "__main__":
    main()
