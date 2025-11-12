from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

# =========================
# New Database URL for sila (MySQL)
# =========================
# Correct format: mysql+pymysql://<username>:<password>@<host>:<port>/<database_name>
DATABASE_URL = "mysql+mysqldb://root:2480@localhost:3306/sila"

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

# Create session
Session = scoped_session(sessionmaker(bind=engine))
SessionLocal = Session

# Base declarative class
Base = declarative_base()
