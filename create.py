from connections import Base, engine
from models import User

# Drop all tables and recreate them to reflect the latest model changes
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

print("Tables recreated with latest columns")