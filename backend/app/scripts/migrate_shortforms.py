import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.database import engine
from sqlalchemy import text

def migrate():
    statements = [
        "DROP TABLE IF EXISTS shortform_likes CASCADE;",
        "DROP TABLE IF EXISTS shortforms CASCADE;",
        """
        CREATE TABLE shortforms (
            id              BIGSERIAL PRIMARY KEY,
            report_id       BIGINT REFERENCES stock_reports(id) ON DELETE SET NULL,
            ticker          VARCHAR(10) NOT NULL REFERENCES stocks(code),
            s3_url          TEXT NOT NULL,
            script          TEXT NOT NULL,
            sentiment       VARCHAR(10) NOT NULL CHECK (sentiment IN ('POS', 'NEG')),
            view_count      INTEGER NOT NULL DEFAULT 0,
            like_count      INTEGER NOT NULL DEFAULT 0,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """,
        """
        CREATE TABLE shortform_likes (
            id            BIGSERIAL PRIMARY KEY,
            shortform_id  BIGINT NOT NULL REFERENCES shortforms(id) ON DELETE CASCADE,
            user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (shortform_id, user_id)
        );
        """,
        """
        CREATE TRIGGER trg_shortforms_updated_at
            BEFORE UPDATE ON shortforms
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """,
        """
        CREATE TRIGGER trg_shortform_likes_updated_at
            BEFORE UPDATE ON shortform_likes
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    ]
    
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
        print("Migration complete: recreated shortforms and shortform_likes tables.")

if __name__ == "__main__":
    migrate()
