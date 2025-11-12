from sqlalchemy import Column, String, Integer, ForeignKey,Boolean
from sqlalchemy.orm import relationship
from connections import Base

# =========================
# User Model (Authentication)
# =========================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False) # roles: admin, student, teacher

    # One-to-one relationship with CompleteProfile
    profile = relationship("CompleteProfile", back_populates="user", uselist=False)

    def __init__(self, username, password, role):
        self.username = username
        self.password = password
        self.role = role


# =========================
# CompleteProfile Model
# =========================
class CompleteProfile(Base):
    __tablename__ = "complete_profile"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Link to User (one-to-one)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User", back_populates="profile")

    # Student Details
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=False)
    contact_no = Column(String(20), nullable=False)
    guardian_name = Column(String(100), nullable=False)
    form = Column(String(20), nullable=False)  # Must have a class (Form 1-4)
    is_active = Column(Boolean, default=False)  # Paid = True, Blocked = False

    def __init__(self, user_id, first_name, last_name, contact_no, guardian_name, form, middle_name=None):
        self.user_id = user_id
        self.first_name = first_name
        self.middle_name = middle_name
        self.last_name = last_name
        self.contact_no = contact_no
        self.guardian_name = guardian_name
        self.form = form


# =========================
# LiveClass Model
# =========================
class LiveClass(Base):
    __tablename__ = "live_classes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    link = Column(String(500), nullable=False)
    time = Column(String(50), nullable=True)
    form = Column(String(200), nullable=True)  # Optional: specify which form/class can access
    subject = Column(String(100), nullable=True)  # Optional: specify subject (e.g., Math, Science)
    active = Column(Boolean, default=False)

class RevisionMaterial(Base):
    __tablename__ = "revision_materials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    subject = Column(String(100), nullable=True)  # Only define once
    form = Column(String(20), nullable=True)
    link = Column(String(255), nullable=True)  # Add this for external links like Google Drive
    file_path = Column(String(255), nullable=True)  # Optional: for uploaded files

# =========================
# Video Model
# =========================
class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    link = Column(String(500), nullable=False)
    form = Column(String(20), nullable=True)  # Optional: specify which form/class can access
    subject = Column(String(100), nullable=True)  # Optional: specify subject (e.g., Math, Science)

class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    user = relationship("User")

    teacher_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False, unique=True)
    subject = Column(String(100), nullable=False)
    is_approved = Column(Boolean, default=False)  # <--- ADD THIS LINE
