from __future__ import annotations

import argparse
import json
from pathlib import Path

from app import app
from webapp.extensions import db
from webapp.models import SafetyResourceDocument, SafetyResourceLink, SafetyResourceRequest
from webapp.services.resource_library import rebuild_document_chunks


def add_document(args: argparse.Namespace) -> None:
    path = Path(args.path)
    binary_data = path.read_bytes()
    with app.app_context():
        document = SafetyResourceDocument(
            family_id=None,
            uploaded_by_id=None,
            filename=path.name,
            content_type=args.content_type,
            file_size=len(binary_data),
            binary_data=binary_data,
            title=args.title or path.stem,
            topic=args.topic,
            audience=args.audience,
            summary=args.summary,
            source_url=args.source_url,
            status="approved",
        )
        db.session.add(document)
        db.session.flush()
        chunk_count = rebuild_document_chunks(document)
        db.session.commit()
        print(json.dumps({"ok": True, "document_id": document.id, "chunks": chunk_count}, indent=2))


def add_link(args: argparse.Namespace) -> None:
    with app.app_context():
        link = SafetyResourceLink(
            family_id=None,
            created_by_id=None,
            title=args.title,
            url=args.url,
            topic=args.topic,
            audience=args.audience,
            summary=args.summary,
            status="approved",
        )
        db.session.add(link)
        db.session.commit()
        print(json.dumps({"ok": True, "link_id": link.id}, indent=2))


def list_requests(_: argparse.Namespace) -> None:
    with app.app_context():
        requests = SafetyResourceRequest.query.order_by(SafetyResourceRequest.created_at.desc()).all()
        payload = [
            {
                "id": item.id,
                "title": item.title,
                "topic": item.topic,
                "audience": item.audience,
                "status": item.status,
                "suggested_url": item.suggested_url,
                "note": item.note,
                "created_at": item.created_at.isoformat(),
            }
            for item in requests
        ]
        print(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage developer-owned Cyber Mzazi safety resources.")
    subparsers = parser.add_subparsers(required=True)

    doc_parser = subparsers.add_parser("add-document", help="Upload and index a developer-approved book/document.")
    doc_parser.add_argument("path")
    doc_parser.add_argument("--title", default="")
    doc_parser.add_argument("--topic", default="Digital safety")
    doc_parser.add_argument("--audience", choices=["all", "parent", "child"], default="all")
    doc_parser.add_argument("--summary", default="")
    doc_parser.add_argument("--source-url", default="")
    doc_parser.add_argument("--content-type", default="application/octet-stream")
    doc_parser.set_defaults(func=add_document)

    link_parser = subparsers.add_parser("add-link", help="Add a developer-approved web resource.")
    link_parser.add_argument("--title", required=True)
    link_parser.add_argument("--url", required=True)
    link_parser.add_argument("--topic", default="Digital safety")
    link_parser.add_argument("--audience", choices=["all", "parent", "child"], default="all")
    link_parser.add_argument("--summary", default="")
    link_parser.set_defaults(func=add_link)

    requests_parser = subparsers.add_parser("requests", help="List parent resource requests.")
    requests_parser.set_defaults(func=list_requests)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
