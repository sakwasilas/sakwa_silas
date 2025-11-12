# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

# # =========================
# # New Database URL for sila (MySQL)
# # =========================
# # Correct format: mysql+pymysql://<username>:<password>@<host>:<port>/<database_name>
# DATABASE_URL = "mysql+mysqldb://root:2480@localhost:3306/sila"

# # Create engine
# engine = create_engine(DATABASE_URL, echo=True)

# # Create session
# Session = scoped_session(sessionmaker(bind=engine))
# SessionLocal = Session

# # Base declarative class
# Base = declarative_base()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base

# =========================
# PostgreSQL Database URL (Render credentials)
# =========================
# Correct format: postgresql://<username>:<password>@<host>:<port>/<database_name>
DATABASE_URL = "postgresql://e_learning_jume_user:PVuDiO9gxiXpuO71skr6Ho0wGO3y6X8x@dpg-d4a9i48dl3ps739lj09g-a.oregon-postgres.render.com:5432/e_learning_jume"

# Create engine
engine = create_engine(DATABASE_URL, echo=True)

# Create session
Session = scoped_session(sessionmaker(bind=engine))
SessionLocal = Session

# Base declarative class
Base = declarative_base()
