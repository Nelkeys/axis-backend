from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, ARRAY, func
from sqlalchemy.orm import relationship
from app.database import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, unique=True)
    time_limit_minutes = Column(Integer, nullable=False, default=30)

    course = relationship("Course", back_populates="quiz")
    questions = relationship(
        "Question",
        back_populates="quiz",
        order_by="Question.order",
        cascade="all, delete-orphan",
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    order = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    options = Column(ARRAY(String), nullable=False)
    correct_index = Column(Integer, nullable=False)

    quiz = relationship("Quiz", back_populates="questions")


class AnswerLog(Base):
    __tablename__ = "answer_logs"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    selected_index = Column(Integer, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())