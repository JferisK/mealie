from copy import deepcopy

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from mealie.db.models.household.planner_document import PlannerDocument


class RevisionConflict(Exception):
    pass


class RepositoryHouseholdPlanner:
    def __init__(self, session: Session, key: str):
        self.session = session
        self.key = key

    def read(self) -> tuple[int, dict]:
        row = self.session.execute(select(PlannerDocument).where(PlannerDocument.id == self.key)).scalar_one_or_none()
        return (row.revision, deepcopy(row.payload)) if row else (0, {})

    def save(self, expected: int, payload: dict) -> int:
        try:
            if expected == 0:
                self.session.add(PlannerDocument(id=self.key, revision=1, payload=payload))
                self.session.flush()
            else:
                result = self.session.execute(
                    update(PlannerDocument)
                    .where(PlannerDocument.id == self.key, PlannerDocument.revision == expected)
                    .values(revision=expected + 1, payload=payload),
                    execution_options={"synchronize_session": False},
                )
                if result.rowcount != 1:
                    raise RevisionConflict("Data changed. Reload and retry with the new revision.")
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise RevisionConflict("Data changed. Reload and retry.") from exc
        except Exception:
            self.session.rollback()
            raise
        return expected + 1
