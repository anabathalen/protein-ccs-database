"""Database schema and repository operations.

SQLite is used for local development. Production should provide a PostgreSQL
DATABASE_URL (for example, a managed Neon database) through Streamlit secrets.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

import pandas as pd
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    and_,
    create_engine,
    delete,
    event,
    exists,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.engine import Engine, RowMapping
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[1]
PAPER_SEED = ROOT / "data" / "papers.json"

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("email", String(320), nullable=False, unique=True),
    Column("nickname", String(40), nullable=False),
    Column("profile_complete", Boolean, nullable=False, default=False),
    Column("active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

papers = Table(
    "papers",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("doi", String(512)),
    Column("doi_normalized", String(512), unique=True),
    Column("pmid", String(32), unique=True),
    Column("title", Text, nullable=False),
    Column("authors", Text, nullable=False, default=""),
    Column("journal", Text, nullable=False, default=""),
    Column("publication_date", String(40)),
    Column("publication_type", String(120)),
    Column("abstract", Text),
    Column("source", String(255), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

entries = Table(
    "entries",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("paper_id", String(36), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
    Column("logger_id", String(36), ForeignKey("users.id"), nullable=False),
    Column("protein", Text, nullable=False),
    Column("ionisation_mode", String(40), nullable=False),
    Column("instrument_family", Text, nullable=False, default=""),
    Column("native", Boolean, nullable=False),
    Column("ims_type", String(40), nullable=False),
    Column("subunits", Integer),
    Column("oligomer_type", String(80)),
    Column("drift_gas_calibration", Text),
    Column("drift_gas_measurement", Text),
    Column("measurement_conditions", Text),
    Column("sample_description", Text),
    Column("supplier_details", Text),
    Column("supplier_details_provided", Boolean, nullable=False, default=False),
    Column("uniprot_id", Text),
    Column("uniprot_id_provided", Boolean, nullable=False, default=False),
    Column("pdb_id", Text),
    Column("pdb_id_provided", Boolean, nullable=False, default=False),
    Column("sequence", Text),
    Column("sequence_provided", Boolean, nullable=False, default=False),
    Column("sequence_mass", Float),
    Column("sequence_mass_provided", Boolean, nullable=False, default=False),
    Column("measured_mass", Float),
    Column("measured_mass_provided", Boolean, nullable=False, default=False),
    Column("status", String(24), nullable=False, default="submitted"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

measurements = Table(
    "measurements",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("entry_id", String(36), ForeignKey("entries.id", ondelete="CASCADE"), nullable=False),
    Column("created_by", String(36), ForeignKey("users.id"), nullable=False),
    Column("measurement_type", String(24), nullable=False),
    Column("charge_state", Integer),
    Column("charge_state_min", Integer),
    Column("charge_state_max", Integer),
    Column("ccs_value", Float, nullable=False),
    Column("error", Float),
    Column("provided", Boolean, nullable=False, default=False),
    Column("from_graph", Boolean, nullable=False, default=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("measurement_type IN ('charge_state', 'global')", name="measurement_type_allowed"),
    CheckConstraint("ccs_value > 0", name="ccs_value_positive"),
    CheckConstraint("error IS NULL OR error >= 0", name="ccs_error_nonnegative"),
    CheckConstraint(
        "(measurement_type = 'charge_state' AND charge_state > 0 AND charge_state_min IS NULL AND charge_state_max IS NULL) "
        "OR (measurement_type = 'global' AND charge_state IS NULL)",
        name="measurement_scope_valid",
    ),
    CheckConstraint("charge_state_min IS NULL OR charge_state_min > 0", name="charge_min_positive"),
    CheckConstraint("charge_state_max IS NULL OR charge_state_max > 0", name="charge_max_positive"),
    CheckConstraint(
        "charge_state_min IS NULL OR charge_state_max IS NULL OR charge_state_min <= charge_state_max",
        name="charge_range_valid",
    ),
)

assignments = Table(
    "assignments",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("paper_id", String(36), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", String(36), ForeignKey("users.id"), nullable=False),
    Column("status", String(24), nullable=False, default="active"),
    Column("assigned_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True)),
)

audit_log = Table(
    "audit_log",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("actor_id", String(36), ForeignKey("users.id"), nullable=False),
    Column("entity_type", String(40), nullable=False),
    Column("entity_id", String(36), nullable=False),
    Column("action", String(40), nullable=False),
    Column("details", Text, nullable=False, default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)


def _records(rows: Iterable[RowMapping]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


class Database:
    """Small repository layer used by all Streamlit pages."""

    def __init__(self, url: str):
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
        if url.startswith("sqlite"):
            event.listen(self.engine, "connect", self._enable_sqlite_foreign_keys)

    @staticmethod
    def _enable_sqlite_foreign_keys(connection: Any, _: Any) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    def initialize(self) -> None:
        metadata.create_all(self.engine)
        self.seed_papers()

    def seed_papers(self) -> int:
        """Insert genuine catalogue papers only; no entries or users are seeded."""

        catalogue = json.loads(PAPER_SEED.read_text(encoding="utf-8"))
        with self.engine.begin() as connection:
            existing = set(connection.execute(select(papers.c.id)).scalars())
            pending = [
                {
                    "id": item["id"],
                    "doi": item.get("doi"),
                    "doi_normalized": item.get("doiNormalized"),
                    "pmid": item.get("pmid"),
                    "title": item["title"],
                    "authors": item.get("authors") or "",
                    "journal": item.get("journal") or "",
                    "publication_date": item.get("publicationDate"),
                    "publication_type": item.get("publicationType"),
                    "abstract": item.get("abstract"),
                    "source": item["source"],
                }
                for item in catalogue
                if item["id"] not in existing
            ]
            if pending:
                connection.execute(insert(papers), pending)
        return len(pending)

    def ensure_user(self, email: str, suggested_name: str) -> dict[str, Any]:
        normalized_email = email.strip().lower()
        nickname = self._clean_nickname(suggested_name or normalized_email.split("@", 1)[0])
        user_id = str(uuid4())
        try:
            with self.engine.begin() as connection:
                row = connection.execute(select(users).where(users.c.email == normalized_email)).mappings().first()
                if row:
                    if not row["active"]:
                        raise PermissionError("This account has been disabled")
                    return dict(row)
                connection.execute(
                    insert(users).values(
                        id=user_id,
                        email=normalized_email,
                        nickname=nickname,
                        profile_complete=False,
                        active=True,
                    )
                )
        except IntegrityError:
            with self.engine.connect() as connection:
                row = connection.execute(select(users).where(users.c.email == normalized_email)).mappings().one()
            return dict(row)
        return {
            "id": user_id,
            "email": normalized_email,
            "nickname": nickname,
            "profile_complete": False,
            "active": True,
        }

    def update_nickname(self, user_id: str, nickname: str) -> str:
        clean = self._clean_nickname(nickname)
        with self.engine.begin() as connection:
            connection.execute(
                update(users)
                .where(users.c.id == user_id)
                .values(nickname=clean, profile_complete=True, updated_at=datetime.now(UTC))
            )
        return clean

    @staticmethod
    def _clean_nickname(value: str) -> str:
        clean = " ".join(value.split())
        if not 2 <= len(clean) <= 40:
            raise ValueError("Nickname must be between 2 and 40 characters")
        return clean

    def counts(self) -> dict[str, int]:
        with self.engine.connect() as connection:
            return {
                "papers": connection.scalar(select(func.count()).select_from(papers)) or 0,
                "entries": connection.scalar(select(func.count()).select_from(entries)) or 0,
                "measurements": connection.scalar(select(func.count()).select_from(measurements)) or 0,
                "users": connection.scalar(select(func.count()).select_from(users)) or 0,
            }

    def find_paper(self, doi_normalized: str) -> dict[str, Any] | None:
        entry_count = (
            select(func.count(entries.c.id))
            .where(and_(entries.c.paper_id == papers.c.id, entries.c.status == "submitted"))
            .scalar_subquery()
        )
        statement = select(papers, entry_count.label("entry_count")).where(
            papers.c.doi_normalized == doi_normalized
        )
        with self.engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
        return dict(row) if row else None

    def create_paper(
        self,
        doi_normalized: str,
        title: str,
        authors: str = "",
        journal: str = "",
        publication_date: str | None = None,
    ) -> dict[str, Any]:
        """Add a user-supplied paper that is not in the seed catalogue."""

        doi = doi_normalized.strip().lower()
        clean_title = title.strip()
        if not doi:
            raise ValueError("DOI is required")
        if not clean_title:
            raise ValueError("Paper title is required")

        existing = self.find_paper(doi)
        if existing:
            return existing

        try:
            with self.engine.begin() as connection:
                connection.execute(
                    insert(papers).values(
                        id=str(uuid4()),
                        doi=doi,
                        doi_normalized=doi,
                        pmid=None,
                        title=clean_title,
                        authors=authors.strip(),
                        journal=journal.strip(),
                        publication_date=self._optional_text(publication_date),
                        publication_type=None,
                        abstract=None,
                        source="user_added",
                    )
                )
        except IntegrityError:
            existing = self.find_paper(doi)
            if existing:
                return existing
            raise ValueError("This paper could not be added") from None

        created = self.find_paper(doi)
        if not created:
            raise ValueError("This paper could not be added")
        return created

    def choose_unlogged_paper(self, user_id: str) -> dict[str, Any] | None:
        now = datetime.now(UTC)
        with self.engine.begin() as connection:
            connection.execute(
                update(assignments)
                .where(and_(assignments.c.status == "active", assignments.c.expires_at < now))
                .values(status="expired")
            )
            already_logged = exists(
                select(entries.c.id).where(
                    and_(entries.c.paper_id == papers.c.id, entries.c.status == "submitted")
                )
            )
            reserved = exists(
                select(assignments.c.id).where(
                    and_(
                        assignments.c.paper_id == papers.c.id,
                        assignments.c.status == "active",
                        assignments.c.expires_at >= now,
                    )
                )
            )
            paper = connection.execute(
                select(papers).where(and_(~already_logged, ~reserved)).order_by(func.random()).limit(1)
            ).mappings().first()
            if not paper:
                return None
            connection.execute(
                insert(assignments).values(
                    id=str(uuid4()),
                    paper_id=paper["id"],
                    user_id=user_id,
                    status="active",
                    expires_at=now + timedelta(days=7),
                )
            )
            return dict(paper)

    def create_entry(
        self,
        user_id: str,
        paper_id: str,
        payload: dict[str, Any],
        measurement_rows: list[dict[str, Any]],
    ) -> str:
        clean_measurements = self._validate_measurements(measurement_rows)
        protein = str(payload.get("protein") or "").strip()
        if not protein:
            raise ValueError("Protein is required")
        entry_id = str(uuid4())
        now = datetime.now(UTC)
        values = {
            "id": entry_id,
            "paper_id": paper_id,
            "logger_id": user_id,
            "protein": protein,
            "ionisation_mode": str(payload.get("ionisation_mode") or "Positive"),
            "instrument_family": str(payload.get("instrument_family") or "").strip(),
            "native": bool(payload.get("native", True)),
            "ims_type": str(payload.get("ims_type") or "DTIMS"),
            "subunits": self._optional_int(payload.get("subunits")),
            "oligomer_type": self._optional_text(payload.get("oligomer_type")),
            "drift_gas_calibration": self._optional_text(payload.get("drift_gas_calibration")),
            "drift_gas_measurement": self._optional_text(payload.get("drift_gas_measurement")),
            "measurement_conditions": self._optional_text(payload.get("measurement_conditions")),
            "sample_description": self._optional_text(payload.get("sample_description")),
            "supplier_details": self._optional_text(payload.get("supplier_details")),
            "supplier_details_provided": bool(payload.get("supplier_details_provided")),
            "uniprot_id": self._optional_text(payload.get("uniprot_id")),
            "uniprot_id_provided": bool(payload.get("uniprot_id_provided")),
            "pdb_id": self._optional_text(payload.get("pdb_id")),
            "pdb_id_provided": bool(payload.get("pdb_id_provided")),
            "sequence": self._optional_text(payload.get("sequence")),
            "sequence_provided": bool(payload.get("sequence_provided")),
            "sequence_mass": self._optional_float(payload.get("sequence_mass")),
            "sequence_mass_provided": bool(payload.get("sequence_mass_provided")),
            "measured_mass": self._optional_float(payload.get("measured_mass")),
            "measured_mass_provided": bool(payload.get("measured_mass_provided")),
            "status": "submitted",
            "created_at": now,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            paper_exists = connection.scalar(select(func.count()).select_from(papers).where(papers.c.id == paper_id))
            if not paper_exists:
                raise ValueError("Select or add a paper before submitting")
            connection.execute(insert(entries).values(**values))
            connection.execute(
                insert(measurements),
                [
                    {
                        "id": str(uuid4()),
                        "entry_id": entry_id,
                        "created_by": user_id,
                        **measurement,
                    }
                    for measurement in clean_measurements
                ],
            )
            connection.execute(
                update(assignments)
                .where(
                    and_(
                        assignments.c.paper_id == paper_id,
                        assignments.c.user_id == user_id,
                        assignments.c.status == "active",
                    )
                )
                .values(status="completed", completed_at=now)
            )
            connection.execute(
                insert(audit_log).values(
                    id=str(uuid4()),
                    actor_id=user_id,
                    entity_type="entry",
                    entity_id=entry_id,
                    action="created",
                    details=json.dumps({"measurements": len(clean_measurements)}),
                )
            )
        return entry_id

    def update_entry(
        self,
        user_id: str,
        entry_id: str,
        paper_id: str,
        payload: dict[str, Any],
        measurement_rows: list[dict[str, Any]],
    ) -> None:
        """Replace an owned entry and its CCS rows in one transaction."""

        clean_measurements = self._validate_measurements(measurement_rows)
        protein = str(payload.get("protein") or "").strip()
        if not protein:
            raise ValueError("Protein is required")
        now = datetime.now(UTC)
        values = {
            "paper_id": paper_id,
            "protein": protein,
            "ionisation_mode": str(payload.get("ionisation_mode") or "Positive"),
            "instrument_family": str(payload.get("instrument_family") or "").strip(),
            "native": bool(payload.get("native", True)),
            "ims_type": str(payload.get("ims_type") or "DTIMS"),
            "subunits": self._optional_int(payload.get("subunits")),
            "oligomer_type": self._optional_text(payload.get("oligomer_type")),
            "drift_gas_calibration": self._optional_text(payload.get("drift_gas_calibration")),
            "drift_gas_measurement": self._optional_text(payload.get("drift_gas_measurement")),
            "measurement_conditions": self._optional_text(payload.get("measurement_conditions")),
            "sample_description": self._optional_text(payload.get("sample_description")),
            "supplier_details": self._optional_text(payload.get("supplier_details")),
            "supplier_details_provided": bool(payload.get("supplier_details_provided")),
            "uniprot_id": self._optional_text(payload.get("uniprot_id")),
            "uniprot_id_provided": bool(payload.get("uniprot_id_provided")),
            "pdb_id": self._optional_text(payload.get("pdb_id")),
            "pdb_id_provided": bool(payload.get("pdb_id_provided")),
            "sequence": self._optional_text(payload.get("sequence")),
            "sequence_provided": bool(payload.get("sequence_provided")),
            "sequence_mass": self._optional_float(payload.get("sequence_mass")),
            "sequence_mass_provided": bool(payload.get("sequence_mass_provided")),
            "measured_mass": self._optional_float(payload.get("measured_mass")),
            "measured_mass_provided": bool(payload.get("measured_mass_provided")),
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(entries.c.logger_id, entries.c.paper_id).where(
                    and_(entries.c.id == entry_id, entries.c.status == "submitted")
                )
            ).mappings().first()
            if not existing:
                raise ValueError("Entry not found")
            if existing["logger_id"] != user_id:
                raise PermissionError("You can only edit entries you logged")
            paper_exists = connection.scalar(
                select(func.count()).select_from(papers).where(papers.c.id == paper_id)
            )
            if not paper_exists:
                raise ValueError("Select or add a paper before saving")
            previous_measurement_count = connection.scalar(
                select(func.count()).select_from(measurements).where(measurements.c.entry_id == entry_id)
            ) or 0
            connection.execute(update(entries).where(entries.c.id == entry_id).values(**values))
            connection.execute(delete(measurements).where(measurements.c.entry_id == entry_id))
            connection.execute(
                insert(measurements),
                [
                    {
                        "id": str(uuid4()),
                        "entry_id": entry_id,
                        "created_by": user_id,
                        "created_at": now,
                        **measurement,
                    }
                    for measurement in clean_measurements
                ],
            )
            connection.execute(
                insert(audit_log).values(
                    id=str(uuid4()),
                    actor_id=user_id,
                    entity_type="entry",
                    entity_id=entry_id,
                    action="updated",
                    details=json.dumps(
                        {
                            "previous_measurements": previous_measurement_count,
                            "measurements": len(clean_measurements),
                            "paper_changed": existing["paper_id"] != paper_id,
                        }
                    ),
                )
            )

    def get_entry_template(self, entry_id: str) -> dict[str, Any] | None:
        """Return one complete entry, its paper, and all CCS rows for duplication."""

        statement = (
            select(
                *entries.c,
                papers.c.doi.label("paper_doi"),
                papers.c.pmid.label("paper_pmid"),
                papers.c.title.label("paper_title"),
                papers.c.authors.label("paper_authors"),
                papers.c.journal.label("paper_journal"),
                papers.c.publication_date.label("paper_publication_date"),
            )
            .select_from(entries.join(papers, entries.c.paper_id == papers.c.id))
            .where(and_(entries.c.id == entry_id, entries.c.status == "submitted"))
        )
        with self.engine.connect() as connection:
            row = connection.execute(statement).mappings().first()
            if not row:
                return None
            measurement_rows = connection.execute(
                select(
                    measurements.c.measurement_type,
                    measurements.c.charge_state,
                    measurements.c.charge_state_min,
                    measurements.c.charge_state_max,
                    measurements.c.ccs_value,
                    measurements.c.error,
                    measurements.c.provided,
                    measurements.c.from_graph,
                )
                .where(measurements.c.entry_id == entry_id)
                .order_by(measurements.c.measurement_type, measurements.c.charge_state)
            ).mappings()

            entry = {column.name: row[column.name] for column in entries.c}
            paper = {
                "id": row["paper_id"],
                "doi": row["paper_doi"],
                "pmid": row["paper_pmid"],
                "title": row["paper_title"],
                "authors": row["paper_authors"],
                "journal": row["paper_journal"],
                "publication_date": row["paper_publication_date"],
            }
            return {
                "entry": entry,
                "paper": paper,
                "measurements": _records(measurement_rows),
            }

    @classmethod
    def _validate_measurements(cls, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        clean: list[dict[str, Any]] = []
        for row in rows:
            if cls._is_blank(row.get("ccs_value")):
                continue
            measurement_type = str(row.get("measurement_type") or "charge_state")
            if measurement_type not in {"charge_state", "global"}:
                raise ValueError("Measurement type must be charge_state or global")
            ccs_value = float(row["ccs_value"])
            if ccs_value <= 0:
                raise ValueError("CCS values must be greater than zero")
            error = cls._optional_float(row.get("error"))
            if error is not None and error < 0:
                raise ValueError("CCS errors cannot be negative")
            charge_state = cls._optional_int(row.get("charge_state"))
            minimum = cls._optional_int(row.get("charge_state_min"))
            maximum = cls._optional_int(row.get("charge_state_max"))
            if measurement_type == "charge_state":
                if not charge_state or charge_state <= 0:
                    raise ValueError("Each charge-state CCS value needs a positive charge state")
                minimum = maximum = None
            else:
                charge_state = None
                if minimum is not None and minimum <= 0 or maximum is not None and maximum <= 0:
                    raise ValueError("Global CCS charge ranges must be positive")
                if minimum is not None and maximum is not None and minimum > maximum:
                    raise ValueError("Global CCS minimum charge cannot exceed its maximum")
            clean.append(
                {
                    "measurement_type": measurement_type,
                    "charge_state": charge_state,
                    "charge_state_min": minimum,
                    "charge_state_max": maximum,
                    "ccs_value": ccs_value,
                    "error": error,
                    "provided": bool(row.get("provided")),
                    "from_graph": bool(row.get("from_graph")),
                }
            )
        if not clean:
            raise ValueError("Add at least one CCS measurement")
        return clean

    def measurement_data(self) -> pd.DataFrame:
        statement = self._measurement_statement().where(entries.c.status == "submitted")
        with self.engine.connect() as connection:
            return pd.DataFrame(_records(connection.execute(statement).mappings()))

    def export_data(self) -> pd.DataFrame:
        """Return every stored field associated with each CCS measurement."""

        statement = self._measurement_statement(include_private=True).where(entries.c.status == "submitted")
        with self.engine.connect() as connection:
            return pd.DataFrame(_records(connection.execute(statement).mappings()))

    @staticmethod
    def _measurement_statement(include_private: bool = False):
        columns = [
            entries.c.id.label("entry_id"),
            papers.c.id.label("paper_id"),
            papers.c.doi.label("doi"),
            papers.c.pmid.label("pmid"),
            papers.c.title.label("paper_title"),
            papers.c.authors,
            papers.c.journal,
            papers.c.publication_date,
            papers.c.publication_type,
            papers.c.source.label("paper_source"),
            entries.c.protein,
            users.c.nickname.label("logged_by"),
            entries.c.ionisation_mode,
            entries.c.instrument_family,
            entries.c.native,
            entries.c.ims_type,
            entries.c.subunits,
            entries.c.oligomer_type,
            entries.c.drift_gas_calibration,
            entries.c.drift_gas_measurement,
            entries.c.measurement_conditions,
            entries.c.sample_description,
            entries.c.supplier_details,
            entries.c.supplier_details_provided,
            entries.c.uniprot_id,
            entries.c.uniprot_id_provided,
            entries.c.pdb_id,
            entries.c.pdb_id_provided,
            entries.c.sequence,
            entries.c.sequence_provided,
            entries.c.sequence_mass,
            entries.c.sequence_mass_provided,
            entries.c.measured_mass,
            entries.c.measured_mass_provided,
            entries.c.status.label("entry_status"),
            entries.c.created_at.label("entry_created_at"),
            entries.c.updated_at.label("entry_updated_at"),
            measurements.c.id.label("measurement_id"),
            measurements.c.measurement_type,
            measurements.c.charge_state,
            measurements.c.charge_state_min,
            measurements.c.charge_state_max,
            measurements.c.ccs_value,
            measurements.c.error,
            measurements.c.provided,
            measurements.c.from_graph,
            measurements.c.created_at.label("measurement_created_at"),
        ]
        if include_private:
            columns.extend([users.c.id.label("logger_id"), users.c.email.label("logger_email"), papers.c.abstract])
        return (
            select(*columns)
            .select_from(
                measurements.join(entries, measurements.c.entry_id == entries.c.id)
                .join(papers, entries.c.paper_id == papers.c.id)
                .join(users, entries.c.logger_id == users.c.id)
            )
            .order_by(entries.c.created_at.desc(), measurements.c.charge_state)
        )

    def leaderboard(self) -> pd.DataFrame:
        statement = (
            select(
                users.c.nickname,
                func.count(func.distinct(entries.c.paper_id)).label("papers_logged"),
                func.count(func.distinct(entries.c.id)).label("protein_entries"),
                func.count(measurements.c.id).label("ccs_values"),
            )
            .select_from(
                users.outerjoin(entries, and_(users.c.id == entries.c.logger_id, entries.c.status == "submitted"))
                .outerjoin(measurements, measurements.c.entry_id == entries.c.id)
            )
            .where(users.c.active.is_(True))
            .group_by(users.c.id, users.c.nickname)
            .order_by(func.count(func.distinct(entries.c.paper_id)).desc(), func.count(measurements.c.id).desc())
        )
        with self.engine.connect() as connection:
            return pd.DataFrame(_records(connection.execute(statement).mappings()))

    @staticmethod
    def _is_blank(value: Any) -> bool:
        return value is None or value == "" or bool(pd.isna(value))

    @classmethod
    def _optional_text(cls, value: Any) -> str | None:
        if cls._is_blank(value):
            return None
        clean = str(value).strip()
        return clean or None

    @classmethod
    def _optional_int(cls, value: Any) -> int | None:
        if cls._is_blank(value):
            return None
        return int(float(value))

    @classmethod
    def _optional_float(cls, value: Any) -> float | None:
        if cls._is_blank(value):
            return None
        return float(value)
