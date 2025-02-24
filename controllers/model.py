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
    quiz = db.relationship('QuizResult',cascade='all, delete', backref=db.backref('User_info_ref', lazy='select'), lazy='select')


class Subject(db.Model):
    __tablename__ = 'subject'
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    chapters = db.relationship('Chapter', backref=db.backref('subject_ref', lazy='select'), lazy='select')
    # def __repr__(self):
    #     return f'<Subject {self.subject}>'


class Quiz(db.Model):
    __tablename__ = 'Quiz'
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    title = db.Column(db.String, nullable=False)
    description= db.Column(db.String, nullable=True)    
    deadline = db.Column(db.DateTime, nullable=False)
    totalNoQues = db.Column(db.Integer, default=0)
    totalMarks = db.Column(db.Integer, default=0)
    passingMarks = db.Column(db.Integer, default=0)
    duration = db.Column(db.Integer, nullable=True)
    questions = db.relationship('Question', backref=db.backref('quiz_ref', lazy='select'),lazy='select')
    


    def is_attempt(self,user_id):
        return QuizResult.query.filter_by(
            user_id=user_id,
            quiz_id=self.id
        ).first() is not None

class Chapter(db.Model):
    __tablename__ = 'chapter'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    chapter = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    quizzes = db.relationship('Quiz', backref=db.backref('chapter_ref', lazy='select'), lazy='select')
    content = db.relationship('content', backref=db.backref('chapter_ref', lazy='select'), lazy='select')
    # def __repr__(self):
    #     return f'<Chapter {self.chapter}>'

class content(db.Model):
    __tablename__ = 'content'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    content_type = db.Column(db.String, nullable=False)
    file_path = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # def __repr__(self):
    #     return f'<Content {self.title}>'

class Question(db.Model):
    __tablename__ = 'question'
    id = db.Column(db.Integer, primary_key=True)    
    quiz_id = db.Column(db.Integer, db.ForeignKey('Quiz.id'), nullable=False)
    question = db.Column(db.String, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # 'mcq' or 'numeric'
    marks = db.Column(db.Integer, nullable=False)
    numeric_answer = db.Column(db.Float, nullable=True)
    tolerance = db.Column(db.Float, nullable=True)
    option1= db.Column(db.String, nullable=True)
    option2 = db.Column(db.String, nullable=True)
    option3 = db.Column(db.String, nullable=True)
    option4 = db.Column(db.String, nullable=True)
    correct = db.Column(db.Boolean, nullable=True)
    explanation = db.Column(db.String, nullable=True)
    answer_type = db.Column(db.String, nullable=True, default="MCQ")
    
    quiz = db.relationship('Quiz', backref='question')
    user_answers = db.relationship('UserAnswers', back_populates='question', lazy=True)

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
    user_id = db.Column(db.Integer, db.ForeignKey('user_info.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_answer = db.Column(db.Text, nullable=True) 
    numeric_answer = db.Column(db.Float, nullable=True)  # Store the actual answer text
    is_correct = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_info = db.relationship('User_Info', backref='UserAnswers')
    question = db.relationship('Question', backref='UserAnswers')

    