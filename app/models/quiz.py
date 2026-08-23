from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, ARRAY, func
from sqlalchemy.orm import relationship
from app.database import Base

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, unique=True)
    time_limit_minutes = Column(Integer, nullable=False, default=30)

    course = relationship("Course", back_populates="quiz")
    questions = relationship("Question", back_populates="quiz", order_by="Question.order", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    order = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    options = Column(ARRAY(String), nullable=False)   # e.g. ["A. ...", "B. ...", "C. ...", "D. ..."]
    correct_index = Column(Integer, nullable=False)    # index into options — NEVER sent to student

    quiz = relationship("Quiz", back_populates="questions")