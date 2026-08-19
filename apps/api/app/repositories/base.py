"""Tenant-scoped repository.

The isolation guarantee rests on three properties of this class:

  1. It cannot be constructed without a `TenantContext`. There is no
     "unscoped" constructor and no default organisation.
  2. It refuses, at construction time, to wrap a model that is not
     `TenantScoped`. A developer who adds a model without an
     `organisation_id` and tries to use it here gets a loud error rather than
     a silently global query.
  3. Every query it builds starts from `_scoped_select()`, which applies the
     `organisation_id` filter. Callers add their own predicates on top; they
     cannot remove that one.

Cross-tenant lookups raise `CrossTenantAccess` (HTTP 404, not 403) so that an
attacker cannot use the response code to discover whether an id exists in
another tenant.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.tenancy import CrossTenantAccess, TenantContext
from app.db.base import Base
from app.db.mixins import TenantScoped

ModelT = TypeVar("ModelT", bound=Base)


class TenantScopedRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: Session, context: TenantContext) -> None:
        if not isinstance(context, TenantContext):
            raise TypeError(
                f"{type(self).__name__} requires a TenantContext; refusing to build "
                f"an unscoped repository."
            )
        if not issubclass(self.model, TenantScoped):
            raise TypeError(
                f"{self.model.__name__} is not TenantScoped and must not be accessed "
                f"through a tenant-scoped repository."
            )
        self.session = session
        self.context = context

    @property
    def organisation_id(self) -> uuid.UUID:
        return self.context.organisation_id

    def _scoped_select(self) -> Select[tuple[ModelT]]:
        """The only entry point for building queries in this repository."""
        return select(self.model).where(
            self.model.organisation_id == self.organisation_id
        )

    def list(self, *predicates: Any, order_by: Any | None = None) -> Sequence[ModelT]:
        stmt = self._scoped_select()
        if predicates:
            stmt = stmt.where(*predicates)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        return self.session.execute(stmt).scalars().all()

    def count(self, *predicates: Any) -> int:
        stmt = select(func.count()).select_from(self.model).where(
            self.model.organisation_id == self.organisation_id
        )
        if predicates:
            stmt = stmt.where(*predicates)
        return self.session.execute(stmt).scalar_one()

    def get(self, entity_id: uuid.UUID) -> ModelT:
        """Fetch one row belonging to this tenant, or raise 404.

        A row that exists but belongs to another organisation is reported
        identically to one that does not exist at all.
        """
        stmt = self._scoped_select().where(self.model.id == entity_id)
        entity = self.session.execute(stmt).scalar_one_or_none()
        if entity is None:
            raise CrossTenantAccess(
                f"{self.model.__name__} {entity_id} not found in this organisation"
            )
        return entity

    def find(self, entity_id: uuid.UUID) -> ModelT | None:
        stmt = self._scoped_select().where(self.model.id == entity_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def add(self, entity: ModelT) -> ModelT:
        """Persist a new row, forcing it into the caller's organisation.

        The organisation is stamped from the context, never taken from the
        request body, so a client cannot create a record inside another tenant
        by supplying an organisation_id.
        """
        entity.organisation_id = self.organisation_id
        self.session.add(entity)
        self.session.flush()
        return entity

    def delete(self, entity_id: uuid.UUID) -> None:
        self.session.delete(self.get(entity_id))
        self.session.flush()
