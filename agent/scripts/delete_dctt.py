"""Delete don-ca-tai-tu-vinh-long (year-round, not a specific event)."""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, ".")
from database import db
db.initialize()
db.delete_entity("don-ca-tai-tu-vinh-long")
print("Deleted don-ca-tai-tu-vinh-long")
