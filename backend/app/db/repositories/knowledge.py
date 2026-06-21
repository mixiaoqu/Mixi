from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select

from app.db.models import DocumentIndexStatus, KnowledgeBase, KnowledgeDocument
from app.db.repositories.base import BaseRepository


class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    model = KnowledgeBase

    def get_by_name(self, workspace_id: uuid.UUID, name: str) -> KnowledgeBase | None:
        return self.get_by(workspace_id=workspace_id, name=name)

    def list_by_workspace(self, workspace_id: uuid.UUID) -> list[KnowledgeBase]:
        stmt = select(KnowledgeBase).where(KnowledgeBase.workspace_id == workspace_id).order_by(KnowledgeBase.created_at.desc())
        return list(self.session.execute(stmt).scalars().all())

    def create_knowledge_base(
        self,
        *,
        workspace_id: uuid.UUID,
        name: str,
        description: str | None = None,
        vector_collection: str | None = None,
        embedding_model: str | None = None,
        config: dict | None = None,
    ) -> KnowledgeBase:
        return self.create(
            workspace_id=workspace_id,
            name=name,
            description=description,
            vector_collection=vector_collection,
            embedding_model=embedding_model,
            config=config or {},
        )


class KnowledgeDocumentRepository(BaseRepository[KnowledgeDocument]):
    model = KnowledgeDocument

    def create_document(
        self,
        *,
        knowledge_base_id: uuid.UUID,
        title: str,
        checksum: str,
        source_type: str = "upload",
        source_uri: str | None = None,
        mime_type: str | None = None,
        size_bytes: int | None = None,
        meta: dict | None = None,
    ) -> KnowledgeDocument:
        return self.create(
            knowledge_base_id=knowledge_base_id,
            title=title,
            checksum=checksum,
            source_type=source_type,
            source_uri=source_uri,
            mime_type=mime_type,
            size_bytes=size_bytes,
            meta=meta or {},
        )

    def list_by_knowledge_base(self, knowledge_base_id: uuid.UUID) -> list[KnowledgeDocument]:
        stmt = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.knowledge_base_id == knowledge_base_id)
            .order_by(KnowledgeDocument.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def mark_indexed(
        self,
        document: KnowledgeDocument,
        *,
        chunk_count: int,
        indexed_at: datetime | None = None,
    ) -> KnowledgeDocument:
        return self.update(
            document,
            chunk_count=chunk_count,
            index_status=DocumentIndexStatus.ready,
            indexed_at=indexed_at or datetime.utcnow(),
        )
