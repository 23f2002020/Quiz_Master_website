from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime, timedelta

db = SQLAlchemy()

class User_Info(db.Model):
    __tablename__ = 'user_info'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    role = db.Column(db.Integer, default=1)
    fullname = db.Column(db.String(120), nullable=False)
    qualification = db.Column(db.String, nullable=False)    
    dob = db.Column(db.Date, nullable=False)
    quiz = db.relationship('QuizResult',cascade='all, delete', backref='user_info', lazy=True)


class Subject(db.Model):
    __tablename__ = 'subject'
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    chapters = db.relationship('Chapter',   backref='subject', lazy=True)


class Quiz(db.Model):
    __tablename__ = 'Quiz'
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    title = db.Column(db.String, nullable=False)
    description= db.Column(db.String, nullable=True)    
    deadline = db.Column(db.DateTime, nullable=False)
    totalNoQues = db.Column(db.Integer, default=0)
    totalMarks = db.Column(db.Integer, default=0)
    duration = db.Column(db.Interval, nullable=True)
    questions = db.relationship('Question', backref='quiz', lazy=True)


class Chapter(db.Model):
    __tablename__ = 'chapter'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    chapter = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    quizzes = db.relationship('Quiz', backref='chapter', lazy=True)


class Question(db.Model):
    __tablename__ = 'question'
    id = db.Column(db.Integer, primary_key=True)    
    quiz_id = db.Column(db.Integer, db.ForeignKey('Quiz.id'), nullable=False)
    question = db.Column(db.String, nullable=False)
    options = db.relationship('Option', backref='question', lazy=True)

class Option(db.Model):
    __tablename__ = 'option'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    option = db.Column(db.String, nullable=True)
    correct = db.Column(db.Boolean, default=False)
    explanation = db.Column(db.String, nullable=True)
    answer_type = db.Column(db.String, nullable=False, default="MCQ")
    

class QuizResult(db.Model):
    __tablename__ = 'QuizResult'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_info.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('Quiz.id'), nullable=False)
    score = db.Column(db.Integer, default=0)
    date_taken = db.Column(db.DateTime, default=datetime.utcnow)

class UserAnswers(db.Model):
    __tablename__ = 'UserAnswers'
    id = db.Column(db.Integer, primary_key=True)
    quiz_res_id = db.Column(db.Integer, db.ForeignKey('QuizResult.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    option_selected = db.Column(db.Integer, db.ForeignKey('option.id'), nullable=False)