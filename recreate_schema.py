import sys
sys.path.insert(0, 'central_agent/backend_agent')

from app.core.database import engine
from app.models.models import Base

# Drop all tables
print('Dropping all tables...')
Base.metadata.drop_all(engine)

# Recreate all tables
print('Creating all tables...')
Base.metadata.create_all(engine)

print('Schema recreated!')
