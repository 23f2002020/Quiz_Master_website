
from flask import Flask, render_template, request,redirect,url_for,flash,session,send_from_directory,abort
from .model import *
from datetime import datetime, timedelta
from flask import current_app as app
import os
from werkzeug.utils import secure_filename
from functools import wraps
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import pandas as pd
import numpy as np
from sqlalchemy import func
from collections import defaultdict

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 0:  # Assuming 0 is admin role
            flash('You do not have permission to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("user_name")
        password = request.form.get("password")
        user = User_Info.query.filter_by(email=username, password=password).first()
        if user:
            session["user_name"] = user.email  
            session["user_id"] = user.id       
            session["role"] = user.role      
            
            if user.role == 0:  
                return redirect(url_for("admin_dashboard", Name=user.email))
            elif user.role == 1:  
                return redirect(url_for("user_interface", id=user.id))
        else:
            return render_template("login.html", err_msg="Invalid username or password")
    
    return render_template("login.html",err_msg="")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        uname=request.form.get("full_name")
        email=request.form.get("user_name")
        password=request.form.get("password")
        qualification=request.form.get("qualification")
        dob1=request.form.get("dob")
        
        try:
            dob = datetime.strptime(dob1, '%d-%m-%Y').date()
        except ValueError:
            return "Invalid Date"
        user = User_Info.query.filter_by(email=email).first()
        if user:
            return render_template("signup.html",err_msg="User already exists")
        user=User_Info(email=email,password=password,fullname=uname,qualification=qualification,dob=dob)
        db.session.add(user)
        db.session.commit()
        return render_template("login.html",err_msg="Registration Successful, try login now")
    return render_template("signup.html",err_msg="")  

@app.route("/adding_subject", methods=["GET"])
def adding_subject():
    return render_template("adding_subject.html")

@app.route("/subject_adding", methods=[ "POST"])
def subject_adding():
    name = request.form.get('name')
    description = request.form.get('description')
    existing_subject = Subject.query.filter_by(subject=name).first()
    if existing_subject:
        flash('Subject already exists!', 'error')
        return redirect(url_for('adding_subject'))
    new_subject = Subject(subject=name, description=description)
    db.session.add(new_subject)
    db.session.commit()
    flash('Subject added successfully!', 'success')
    return redirect(url_for('admin_dashboard',Name=name,subject_id=new_subject.id))

@app.route("/admin_dashboard/<Name>")
def admin_dashboard(Name):
    # subjects = Subject.query.all() 
    # chapters = Chapter.query.all()
    users = User_Info.query.all()
    subjects = get_subjects()
    chapters = get_chapters()
    quizzes = Quiz.query.all()
    contents = content.query.all()
    admin_name= session.get("user_name")
    admin_info = User_Info.query.get(admin_name)
    return render_template("admin_dashboard.html",Name=Name, subjects=subjects,chapters=chapters,quizzes=quizzes, content=contents, users = users,user_info=admin_info)

@app.route("/user/<id>")
@login_required
def user_interface(id):
    # Verify the user is accessing their own interface
    if int(id) != session.get('user_id') and session.get('role') != 0:
        flash("You can only access your own dashboard", "error")
        return redirect(url_for('user_interface', id=session.get('user_id')))

    user_info = User_Info.query.get_or_404(id)
    subjects = get_subjects()
    chapters = get_chapters()
    
    # Get all content accessible to the user
    accessible_content = []
    for chapter in chapters:
        accessible_content.extend(content.query.filter_by(chapter_id=chapter.id).all())
    
    # Get quiz results with more details
    quiz_results = {}
    for chapter in chapters:
        for quiz in chapter.quizzes:
            result = QuizResult.query.filter_by(user_id=id, quiz_id=quiz.id).first()
            if result:
                quiz_results[quiz.id] = {
                    'result_id': result.id,
                    'score': result.score,
                    'date_taken': result.date_taken,
                    'time_taken': result.time_taken,
                    'total_marks': quiz.totalMarks,
                    'passed': result.score >= quiz.passingMarks
                }
    
    return render_template("user_interface.html",
                         id=id,
                         subjects=subjects,
                         chapters=chapters,
                         content=accessible_content,
                         quiz_results=quiz_results,
                         user_info=user_info,
                         now=datetime.now())



@app.route("/chapter/<int:chapter_id>")
def view_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    subject = Subject.query.get_or_404(chapter.subject_id)
    contents = content.query.filter_by(chapter_id=chapter_id).all()
    quizzes = Quiz.query.filter_by(chapter_id=chapter_id).all()
    return render_template("view_chapter.html", chapter=chapter, content=contents, quizzes=quizzes, subject=subject)

# Configure allowed extensions
upload_folder = 'static/uploads'
allowed_extention = {
    'video': {'mp4'},
    'pdf':{'pdf'},
    "ppt":{'ppt','pptx'},
    "doc":{'doc','docx'}
}

def allowed_file(filename, content_type=None):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extention[content_type]

@app.route("/add_chapter/<int:subject_id>", methods=["GET", "POST"])
def add_chapter(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    if request.method == "POST":
        # ... [your existing chapter creation code] ...
        
        for content_type, form_key in content_types.items():
            if form_key in request.files:
                file = request.files[form_key]
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                    
                    if ext not in ALLOWED_EXTENSIONS:
                        flash(f"Invalid file extension for {content_type}", "error")
                        continue
                        
                    # Create directory structure: uploads/chapter_id/content_type/
                    chapter_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(chapter.id), content_type)
                    os.makedirs(chapter_dir, exist_ok=True)
                    
                    # Save file
                    file_path = os.path.join(chapter_dir, filename)
                    file.save(file_path)
                    
                    # Store relative path in database
                    relative_path = os.path.join(str(chapter.id), content_type, filename)
                    
                    new_content = content(
                        title=filename,
                        content_type=content_type,
                        chapter_id=chapter.id,
                        file_path=relative_path  # Store relative path
                    )
                    db.session.add(new_content)
                    
    

@app.route("/add_quiz/<int:chapter_id>", methods=["GET","POST"])
def add_quiz(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    subject = Subject.query.get_or_404(chapter.subject_id)
    if request.method == "POST":
        try:
            quiz_name = request.form.get('quiz_name')
            description = request.form.get('description')
            duration = request.form.get('duration')
            deadline_str = request.form.get('quiz_deadline')
            total_marks = request.form.get('totalMarks')
            passing_marks = request.form.get('passing_marks')
            total_questions = request.form.get('totalNoQues')

            # Validate required fields
            if not all([quiz_name, description, duration, deadline_str, 
                        total_marks, passing_marks, total_questions]):
                flash('All fields are required', 'error')
                return redirect(url_for('add_quiz', chapter_id=chapter_id))

            # Convert string inputs to appropriate types
            try:
                duration = int(duration)
                total_marks = int(total_marks)
                passing_marks = int(passing_marks)
                total_questions = int(total_questions)
                deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
            except (ValueError, TypeError) as e:
                flash('Invalid input values. Please check all fields.', 'error')
                return redirect(url_for('add_quiz', chapter_id=chapter_id))

            # Create new quiz with matching field names
            new_quiz = Quiz(
                title=quiz_name,
                description=description,
                duration=duration,
                deadline=deadline,
                totalMarks=total_marks,  
                passingMarks=passing_marks,
                totalNoQues=total_questions,
                chapter_id=chapter_id
            )
            db.session.add(new_quiz)
            db.session.commit()
            
            flash('Quiz created successfully!', 'success')
            return redirect(url_for('add_questions', quiz_id=new_quiz.id))
        except Exception as e:
            
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('add_quiz', chapter_id=chapter_id))
    chapter = Chapter.query.get_or_404(chapter_id)
    return render_template('add_quiz.html', chapter=chapter)
    


# Now apply the decorator to admin-only routes
@app.route("/add_questions/<int:quiz_id>/<type>", methods=["GET", "POST"])
@app.route("/add_questions/<int:quiz_id>", methods=["GET", "POST"])


def add_questions(quiz_id, type="mcq"):
    
    quiz = Quiz.query.get_or_404(quiz_id)
    if not type:
        type="mcq"
    
    existing_question_count = Question.query.filter_by(quiz_id=quiz_id).count()
    
    remaining_questions = max(quiz.totalNoQues - existing_question_count,0)
    return render_template('add_questions.html', quiz=quiz, question_type=type, remaining_questions=remaining_questions)

@app.route("/save_question/<int:quiz_id>", methods=["POST","GET"])
def save_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == "POST":
        try:
            question_type = request.form.get('question_type')
            question = request.form.get('question',"").strip()
            marks = request.form.get('marks',"1").strip()
            marks = int(marks)
            correct = request.form.get('correct',"").strip()

            # if not all([question_type, question, marks]):
            #     flash("Question text and Marks are required", "error")
            #     return redirect(url_for('add_questions', quiz_id=quiz_id, type=question_type))
            existing_question=Question.query.filter_by(quiz_id=quiz_id, question=request.form.get('question')).first()
            if existing_question:
                flash("Question already exists", "error")
                return redirect(url_for('add_questions', quiz_id=quiz_id, type=question_type))
            # Create new question with common fields
            new_question = Question(
                question=question,
                question_type=question_type,
                marks=marks,
                quiz_id=quiz_id,
                option1=None,
                option2=None,
                option3=None,
                option4=None,
                correct=None,
                numeric_answer=None,
                tolerance=None
            )
            
            if question_type == 'mcq':
                # Get all options
                option1 = request.form.get('option1')
                option2 = request.form.get('option2')
                option3 = request.form.get('option3')
                option4 = request.form.get('option4')
                correct = correct
            # Handle specific question type fields
                new_question.option1 = option1 if option1 else None
                new_question.option2 = option2 if option2 else None
                new_question.option3 = option3 if option3 else None
                new_question.option4 = option4 if option4 else None
                new_question.correct = correct

            
            elif question_type == 'numeric':
                numeric_answer = request.form.get('numeric_answer')
                tolerance = request.form.get('tolerance')
                
                if not all([numeric_answer, tolerance]):
                    flash( "Numeric answer and tolerance are required", 'error')
                    return redirect(url_for('add_questions', quiz_id=quiz_id, type='numeric'))
                else:
                    new_question.numeric_answer = None
                    new_question.tolerance = None
                
                new_question.numeric_answer = float(numeric_answer)
                new_question.tolerance = float(tolerance)
            answer_type = question_type
            new_question.answer_type = answer_type
            explanation = request.form.get('explanation')
            new_question.explanation = explanation
            db.session.add(new_question)
            db.session.commit()
            
            existing_questions = Question.query.filter_by(quiz_id=quiz_id).count()
            remaining_questions = max(quiz.totalNoQues - existing_questions, 0)
          
            
            if "add_another" in request.form and remaining_questions > 0:
                flash('Question saved! Add another.', 'success')
                return redirect(url_for('add_questions', quiz_id=quiz_id, type=question_type))

            if "save_and_finish" in request.form or remaining_questions == 0:
                return redirect(url_for('admin_dashboard', Name=session.get('user_name', '')))
            
        except ValueError as e:
            flash(f'Invalid numeric value: {str(e)}', 'error')
            return redirect(url_for('add_questions', quiz_id=quiz_id, type=question_type))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('add_questions', quiz_id=quiz_id, type=question_type))

@app.route("/edit_questions/<int:quiz_id>", methods=["POST"])
def edit_questions(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    for question in quiz.questions:
        question_text = request.form.get(f"question_{question.id}")
        if question_text:
            question.question = question_text
        
        if question.question_type == "mcq":
            question.option1 = request.form.get(f"option1_{question.id}", question.option1)
            question.option2 = request.form.get(f"option2_{question.id}", question.option2)
            question.option3 = request.form.get(f"option3_{question.id}", question.option3)
            question.option4 = request.form.get(f"option4_{question.id}", question.option4)
            question.correct = request.form.get(f"correct_{question.id}", question.correct)

        elif question.question_type == "numeric":
            numeric_answer = request.form.get(f"numeric_answer_{question.id}")
            tolerance = request.form.get(f"tolerance_{question.id}")
            if numeric_answer and tolerance:
                try:
                    question.numeric_answer = float(numeric_answer)
                    question.tolerance = float(tolerance)
                except ValueError:
                    flash(f"Invalid numeric input for question {question.id}", "error")
                    return redirect(url_for("view_chapter", chapter_id=quiz.chapter_id))

    db.session.commit()
    flash("Questions updated successfully!", "success")
    return redirect(url_for("view_chapter", chapter_id=quiz.chapter_id))


def get_subjects():
    allsubject = Subject.query.all()
    return allsubject

def get_chapters():
    allchapter = Chapter.query.all()
    return allchapter

@app.route("/start_quiz/<int:quiz_id>", methods=["GET"])
def start_quiz(quiz_id):
    user_info = session.get("user_id")
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()

    if datetime.now() > quiz.deadline:
        flash('Quiz deadline has passed "QUIZ EXPIRED"', 'error')
        return redirect(url_for('user_interface',id=session.get("user_id")))
    
    if QuizResult.query.filter_by(user_id=session.get('user_info.id'),quiz_id=quiz_id).first():
        flash('You have already attempted this quiz', 'error')
        return redirect(url_for('user_interface', id=session.get("user_id")))
    return render_template('start_quiz.html', quiz=quiz,questions=questions, user_info=user_info)

@app.route("/attempt_quiz/<int:quiz_id>", methods=["POST", "GET"])
def attempt_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    user_info = session.get('user_info')
    # user_info_id = user_info.id  # Ensure user_info is always defined

    if request.method == "POST":
        session['quiz_start_time'] = float(datetime.now().timestamp())
        session['quiz_id'] = quiz_id
        session['quiz_answers'] = {}

        return render_template(
            "attempt_quiz.html",
            quiz=quiz,
            current_question=0,
            start_time=session['quiz_start_time'],
            user_info=user_info
        )

    if 'quiz_start_time' not in session or session.get('quiz_id') != quiz_id:
        return redirect(url_for('start_quiz', quiz_id=quiz_id))

    
    try:
        quiz_duration = int(quiz.duration)
    except ValueError:
        flash("Error: Quiz duration is not a valid number.", "error")
        return redirect(url_for('start_quiz', quiz_id=quiz_id))

    
    time_spent = datetime.now().timestamp() - session.get('quiz_start_time', datetime.now().timestamp())


    remaining_time = max(0, quiz_duration * 60 - int(time_spent))


    if remaining_time <= 0:
        return submit_quiz(quiz_id)

    return render_template(
        'attempt_quiz.html',
        quiz=quiz,
        remaining_time=remaining_time,
        user_info=user_info
    )


@app.route("/submit_quiz/<int:quiz_id>", methods=["POST"])
def submit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    user_id = int(session.get("user_id"))

    #  Ensure user has started the quiz
    if 'quiz_start_time' not in session:
        flash("Error: No active quiz session found.", "error")
        return redirect(url_for("user_interface", id=user_id))

    #  Convert session start time to float before using datetime.fromtimestamp()
    start_time = datetime.fromtimestamp(float(session['quiz_start_time']))
    end_time = datetime.now()
    time_taken = (end_time - start_time).total_seconds()  # Store time in seconds

    score = 0
    answers = {}

    for question in questions:
        question_id = int(question.id)  #  Ensure question_id is an integer
        answer_key = f"q{question_id}"
        selected_answer = request.form.get(answer_key)
        is_correct = False
        numeric_answer = None  #  Initialize numeric_answer

        if selected_answer:
            if question.question_type == "numeric":
                try:
                    selected_answer = float(selected_answer)  
                    correct_answer = float(question.numeric_answer)
                    tolerance = float(question.tolerance) if question.tolerance else 0.0

                    #  Compare correctly within tolerance range
                    if abs(selected_answer - correct_answer) <= tolerance:
                        is_correct = True
                        score += question.marks
                    numeric_answer = selected_answer
                except ValueError:
                    flash(f"Invalid numeric input for question {question_id}", "error")
                    return redirect(url_for("start_quiz", quiz_id=quiz_id))

            else:  # Multiple Choice Questions (MCQ)
                correct_answer_letter = question.correct
                correct_answer = None

                if correct_answer_letter == 'A':
                    correct_answer = question.option1
                elif correct_answer_letter == 'B':
                    correct_answer = question.option2
                elif correct_answer_letter == 'C':
                    correct_answer = question.option3
                elif correct_answer_letter == 'D':
                    correct_answer = question.option4

                if selected_answer == correct_answer:
                    is_correct = True
                    score += question.marks

            # Store answers in the dictionary
            answers[question_id] = selected_answer  

            # Store user answers in the database
            user_answer = UserAnswers(
                user_id=user_id,
                quiz_id=quiz_id,
                question_id=question_id,
                selected_answer=selected_answer if question.question_type != "numeric" else None,  
                numeric_answer=numeric_answer if question.question_type == "numeric" else None,    
                is_correct=is_correct
            )
            db.session.add(user_answer)

    # Save quiz result
    quiz_result = QuizResult(
        user_id=user_id,
        quiz_id=quiz_id,
        score=score,
        date_taken=start_time,
        time_taken=int(time_taken)  # Ensure time_taken is stored as an integer
    )
    db.session.add(quiz_result)

    # Commit all database changes
    db.session.commit()

    # Clean up session data
    session.pop('quiz_start_time', None)
    session.pop('quiz_id', None)

    return redirect(url_for('quiz_result', result_id=quiz_result.id))


    # if "quiz_results" not in session:
    #     session["quiz_results"] = {}
    # session["quiz_results"][quiz_id] = quiz_result.id
    
    # session.pop('quiz_start_time', None)
    # session.pop('quiz_id', None)

    
    # return redirect(url_for('quiz_result', result_id=quiz_result.id))


@app.route("/quiz_result/<int:result_id>")
def quiz_result(result_id):
    result = QuizResult.query.get_or_404(result_id)
    quiz = Quiz.query.filter_by(id=result.quiz_id).first()
    user_answers = UserAnswers.query.filter_by(user_id=result.user_id, quiz_id=result.quiz_id).all()
    user_info = User_Info.query.get(result.user_id)
    questions = Question.query.filter_by(quiz_id=result.quiz_id).all()
    question_details = []
    for question in questions:
        user_answer = next((ua for ua in user_answers if ua.question_id == question.id), None)
        
        correct_option_text = None
        if question.question_type == "mcq":
            if question.correct == "A":
                correct_option_text = question.option1
            elif question.correct == "B":
                correct_option_text = question.option2
            elif question.correct == "C":
                correct_option_text = question.option3
            elif question.correct == "D":
                correct_option_text = question.option4
        
        question_details.append({
            "question": question.question,
            "question_type": question.question_type,
            "user_answer": user_answer.selected_answer if user_answer else None,
            "numeric_answer": user_answer.numeric_answer if user_answer else None,
            "correct_answer": question.correct if question.question_type == "mcq" else question.numeric_answer,
            "is_correct": user_answer.is_correct if user_answer else False,
            "correct_option_text": correct_option_text,
            "explanation": question.explanation
        })
    
    return render_template('result.html', result=result, quiz=quiz, question_details=question_details,user_info=user_info)
    

@app.route("/delete_content/<int:content_id>", methods=["POST"])
def delete_content(content_id):
    content_item = content.query.get_or_404(content_id)
    chapter_id = content_item.chapter_id

    try:
        full_path = os.path.join(app.root_path, 'static/uploads', content_item.file_path)
        if os.path.exists(full_path):
            os.remove(full_path)
    except FileNotFoundError:
        pass

    db.session.delete(content_item)
    db.session.commit()
    flash("Content deleted successfully!", "success")
    return redirect(url_for("view_chapter", chapter_id=chapter_id))


@app.route("/delete_quiz/<int:quiz_id>", methods=["POST"])
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    Question.query.filter_by(quiz_id=quiz.id).delete()
    UserAnswers.query.filter_by(quiz_id=quiz.id).delete()
    QuizResult.query.filter_by(quiz_id=quiz.id).delete()
    db.session.delete(quiz)
    db.session.commit()

    flash("Quiz deleted successfully!", "success")
    return redirect(url_for("admin_dashboard", Name=session.get('user_name', 'Admin')))

@app.route("/edit_quiz/<int:quiz_id>", methods=["GET", "POST"])
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    if request.method == "POST":
        
        new_deadline_str = request.form.get("deadline")
        try:
            new_deadline = datetime.strptime(new_deadline_str, "%Y-%m-%dT%H:%M")
        except ValueError:
            flash("Invalid date format. Please use the correct format.", "error")
            return redirect(url_for("edit_quiz", quiz_id=quiz_id))

        quiz.deadline = new_deadline
        db.session.commit()

        flash("Quiz deadline updated successfully!", "success")
        return redirect(url_for("admin_dashboard", Name=session.get("user_name", "Admin")))

    return render_template("edit_quiz.html", quiz=quiz)


# At the top of controller.py with other configurations
upload_folder = 'static/uploads'
app.config['UPLOAD_FOLDER'] = upload_folder  # Or your preferred path
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Update your download_file route

@app.route('/download/<path:filename>')
def download_file(filename):
    try:
        # Build the absolute path to the file
        uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
        file_path = os.path.join(uploads_dir, filename)

        # Check if file exists
        if not os.path.isfile(file_path):
            flash("File not found.", "error")
            return redirect(url_for("user_interface", id=session.get("user_id")))

        # Determine whether to download or view based on file type
        download = request.args.get('download', 'false').lower() == 'true'
        
        # Guess MIME type
        ext = filename.lower().rsplit('.', 1)[-1]
        content_types = {
            'pdf': 'application/pdf',
            'ppt': 'application/vnd.ms-powerpoint',
            'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'mp4': 'video/mp4'
        }
        content_type = content_types.get(ext, 'application/octet-stream')

        return send_from_directory(
            uploads_dir,
            filename,
            as_attachment=download,  # Only force download if ?download=true
            mimetype=content_type
        )
    except Exception as e:
        flash(f"Error accessing file: {str(e)}", "error")
        return redirect(url_for("user_interface", id=session.get("user_id")))


@app.route("/scores/<int:user_id>")
def scores(user_id):
    user_results = QuizResult.query.filter_by(user_id=user_id).all()
    user_info = User_Info.query.filter_by(id=user_id).first()
    return render_template("scores.html", user_results=user_results, user_info=user_info)

@app.route("/summary/<int:user_id>")
def summary(user_id):
    # Fetch user information
    user_info = User_Info.query.get_or_404(user_id)
    
    # Fetch all quiz results for the user
    user_results = QuizResult.query.filter_by(user_id=user_id).all()
    
    # Calculate quick stats
    total_quizzes = Quiz.query.count()
    completed_quizzes = len({result.quiz_id for result in user_results})

    incomplete_quizzes = total_quizzes - completed_quizzes
    
    # Calculate average score and performance metrics
    avg_score = 0
    if user_results:
        avg_score = sum(result.score for result in user_results) / len(user_results)
    
    # Performance label based on average score
    performance_label = "Excellent" if avg_score >= 85 else \
                       "Good" if avg_score >= 70 else \
                       "Average" if avg_score >= 50 else "Needs Improvement"
    
    # Calculate improvement rate (last 3 quizzes vs previous 3)
    improvement_rate = 0
    if len(user_results) >= 6:
        recent_avg = sum(r.score for r in user_results[-3:]) / 3
        older_avg = sum(r.score for r in user_results[-6:-3]) / 3
        improvement_rate = ((recent_avg - older_avg) / older_avg) * 100 if older_avg != 0 else 0
    
    # Subject performance analysis
    subject_scores = defaultdict(list)
    for result in user_results:
        subject_name = result.quiz.chapter_ref.subject_ref.subject
        subject_scores[subject_name].append(result.score *10)
    
    subject_perf = []
    for subject, scores in subject_scores.items():
        subject_perf.append({
            'subject': subject,
            'average': sum(scores) / len(scores),
            'highest': max(scores),
            'lowest': min(scores),
            'attempts': len(scores),
            'improvement': calculate_subject_improvement(subject, user_id)
        })
    
    # Time management analysis
    time_data = [{
        'quiz': result.quiz.title,
        'time_taken': result.time_taken,
        'time_per_question': result.time_taken / result.quiz.totalNoQues if result.quiz.totalNoQues else 0,
        'score': result.score
    } for result in user_results if result.time_taken]
    
    # Class comparison data
    class_avg_scores = get_class_averages()
    class_comparison = []
    for subject, data in subject_scores.items():
        user_avg = sum(data) / len(data)
        class_avg = class_avg_scores.get(subject , 0)
        class_comparison.append({
            'subject': subject,
            'user_avg': user_avg,
            'class_avg': class_avg,
            'difference': user_avg - class_avg
        })
    
    # Generate visualizations
    charts = {
        'subject_performance': generate_subject_performance_chart(subject_perf),
        'completion_status': generate_completion_chart(completed_quizzes, incomplete_quizzes),
        'performance_trend': generate_performance_trend(user_results),
        'time_management': generate_time_management_chart(time_data),
        'class_comparison': generate_class_comparison_chart(class_comparison),
        'weak_areas': generate_weak_areas_chart(subject_perf)
    }
    
    # Generate improvement suggestions
    suggestions = generate_improvement_suggestions(subject_perf, time_data, improvement_rate)
    
    return render_template(
        "summary.html",
        user_info =user_info,
        quick_stats={
            'total_quizzes': total_quizzes,
            'completed': completed_quizzes,
            'incomplete': incomplete_quizzes,
            'avg_score': avg_score,
            'performance_label': performance_label,
            'improvement_rate': improvement_rate
        },
        subject_perf=sorted(subject_perf, key=lambda x: x['average'], reverse=True),
        time_data=time_data,
        class_comparison=class_comparison,
        charts=charts,
        suggestions=suggestions
    )

def calculate_subject_improvement(subject_name, user_id):
    """Calculate improvement rate for a specific subject"""
    subject_results = QuizResult.query.join(Quiz).join(Chapter).join(Subject)\
        .filter(Subject.subject == subject_name, QuizResult.user_id == user_id)\
        .order_by(QuizResult.date_taken).all()
    
    if len(subject_results) >= 4:
        recent = subject_results[-2:]
        older = subject_results[:2]
        recent_avg = sum(r.score for r in recent) / len(recent)
        older_avg = sum(r.score for r in older) / len(older)
        return ((recent_avg - older_avg) / older_avg) * 100 if older_avg != 0 else 0
    return 0

def get_class_averages():
    """Calculate average scores for each subject across all users"""
    results = db.session.query(
        Subject.subject,
        func.avg(QuizResult.score * 10).label('avg_score')
    ).join(Quiz).join(Chapter).join(Subject)\
     .group_by(Subject.subject).all()
    return {subject: avg_score for subject, avg_score in results}

def generate_subject_performance_chart(subject_data):
    """Generate subject performance bar chart"""
    plt.figure(figsize=(10, 6))
    sns.set_theme(style="whitegrid")
    
    subjects = [d['subject'] for d in subject_data]
    avgs = [d['average'] for d in subject_data]
    
    ax = sns.barplot(x=subjects, y=avgs, palette="viridis")
    ax.set(xlabel='Subjects', ylabel='Average Score', title='Subject-wise Performance')
    plt.xticks(rotation=45)
    plt.ylim(0, 100)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def generate_completion_chart(completed, incomplete):
    """Generate quiz completion pie chart"""
    plt.figure(figsize=(8, 8))
    labels = ['Completed', 'Incomplete']
    sizes = [completed, incomplete]
    colors = ['#4CAF50', '#F44336']
    explode = (0.1, 0)
    
    plt.pie(sizes, explode=explode, labels=labels, colors=colors,
            autopct='%1.1f%%', shadow=True, startangle=140)
    plt.title('Quiz Completion Status')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def generate_performance_trend(results):
    """Generate performance trend line chart"""
    if not results:
        return None
        
    dates = [r.date_taken.strftime('%Y-%m-%d') for r in results]
    scores = [r.score for r in results]
    
    plt.figure(figsize=(10, 6))
    sns.lineplot(x=dates, y=scores, marker='o', color='#2196F3', linewidth=2.5)
    plt.title('Performance Trend Over Time')
    plt.xlabel('Date')
    plt.ylabel('Score')
    plt.xticks(rotation=45)
    plt.grid(True)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def generate_time_management_chart(time_data):
    """Generate time management scatter plot"""
    if not time_data:
        return None
        
    df = pd.DataFrame(time_data)
    
    plt.figure(figsize=(10, 6))
    sns.scatterplot(data=df, x='time_per_question', y='score', hue='quiz',
                   palette='deep', s=100)
    plt.title('Time Management vs Performance')
    plt.xlabel('Time per Question (seconds)')
    plt.ylabel('Score')
    plt.axvline(x=60, color='r', linestyle='--', label='Ideal Time')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def generate_class_comparison_chart(comparison_data):
    """Generate class comparison radar chart"""
    if not comparison_data:
        return None
        
    subjects = [d['subject'] for d in comparison_data]
    user_avgs = [d['user_avg'] for d in comparison_data]
    class_avgs = [d['class_avg'] for d in comparison_data]
    
    angles = np.linspace(0, 2*np.pi, len(subjects), endpoint=False).tolist()
    angles += angles[:1]  # Close the polygon
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    
    # Plot user averages
    values = user_avgs + user_avgs[:1]
    ax.plot(angles, values, color='#4CAF50', linewidth=2, label='Your Score')
    ax.fill(angles, values, color='#4CAF50', alpha=0.25)
    
    # Plot class averages
    values = class_avgs + class_avgs[:1]
    ax.plot(angles, values, color='#2196F3', linewidth=2, label='Class Average')
    ax.fill(angles, values, color='#2196F3', alpha=0.25)
    
    ax.set_theta_offset(np.pi/2)
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.degrees(angles[:-1]), subjects)
    
    ax.set_rlabel_position(0)
    plt.yticks([20, 40, 60, 80, 100], ["20", "40", "60", "80", "100"], color="grey", size=7)
    plt.ylim(0, 100)
    
    plt.title('Performance Compared to Class', y=1.1)
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def generate_weak_areas_chart(subject_data):
    """Generate weak areas heatmap"""
    if not subject_data:
        return None
        
    df = pd.DataFrame(subject_data)
    df['weakness_score'] = 100 - df['average']  # Higher score means weaker area
    
    plt.figure(figsize=(10, 6))
    sns.heatmap(df[['subject', 'weakness_score']].set_index('subject').T,
                cmap='YlOrRd', annot=True, fmt='.1f', linewidths=.5)
    plt.title('Weak Areas Identification')
    plt.yticks([])
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close()
    return base64.b64encode(buf.getvalue()).decode('utf-8')

def generate_improvement_suggestions(subject_perf, time_data, improvement_rate):
    """Generate personalized improvement suggestions"""
    suggestions = []
    
    # Subject-based suggestions
    weak_subjects = sorted(subject_perf, key=lambda x: x['average'])[:2]
    for subj in weak_subjects:
        suggestions.append({
            'type': 'subject',
            'message': f"Focus more on {subj['subject']} (your score: {subj['average']:.1f}%)",
            'priority': 'high'
        })
    
    # Time management suggestions
    if time_data:
        avg_time = sum(t['time_per_question'] for t in time_data) / len(time_data)
        if avg_time > 90:
            suggestions.append({
                'type': 'time',
                'message': "You're spending too much time per question (avg: {:.1f}s). Practice timed quizzes.".format(avg_time),
                'priority': 'medium'
            })
    
    # Improvement rate suggestion
    if improvement_rate > 0:
        suggestions.append({
            'type': 'progress',
            'message': f"Great job! Your scores are improving (+{improvement_rate:.1f}% recently)",
            'priority': 'positive'
        })
    elif improvement_rate < 0:
        suggestions.append({
            'type': 'progress',
            'message': f"Your recent scores are dropping ({improvement_rate:.1f}%). Review previous quizzes.",
            'priority': 'high'
        })
    
    # General suggestions
    suggestions.extend([
        {
            'type': 'general',
            'message': "Review incorrect answers from past quizzes",
            'priority': 'medium'
        },
        {
            'type': 'general',
            'message': "Take practice quizzes on weak subjects",
            'priority': 'high'
        }
    ])
    
    return suggestions

@app.route("/search")
@login_required
@admin_required
def search():
    query = request.args.get('query', '').strip()
    if not query:
        flash("Please enter a search term.", "error")
        return redirect(url_for('admin_dashboard', Name=session.get('user_name', 'Admin')))

    try:
        # Get admin name from session for the dashboard link
        admin_name = session.get('user_name', 'Admin')
        
        # Search queries
        users = User_Info.query.filter(User_Info.fullname.ilike(f'%{query}%')).all()
        subjects = Subject.query.filter(Subject.subject.ilike(f'%{query}%')).all()
        chapters = Chapter.query.filter(Chapter.chapter.ilike(f'%{query}%')).all()
        quizzes = Quiz.query.filter(Quiz.title.ilike(f'%{query}%')).all()

        return render_template('search.html',
                            query=query,
                            users=users,
                            subjects=subjects,
                            chapters=chapters,
                            quizzes=quizzes,
                            admin_name=admin_name)  # Pass admin_name to template
    
    except Exception as e:
        flash(f"An error occurred during search: {str(e)}", "error")
        return redirect(url_for('admin_dashboard', Name=session.get('user_name', 'Admin')))

@app.route("/user_performance/<int:user_id>")
def user_performance(user_id):
    user = User_Info.query.get_or_404(user_id)
    quiz_results = QuizResult.query.filter_by(user_id=user_id).all()
    
    # Prepare data for overall performance
    quiz_titles = [result.quiz.title for result in quiz_results]
    scores = [result.score for result in quiz_results]

    # Generate bar chart for overall performance
    plt.figure(figsize=(10, 5))
    plt.bar(quiz_titles, scores, color='blue')
    plt.xlabel('Quiz Titles')
    plt.ylabel('Scores')
    plt.title(f'{user.fullname}\'s Overall Performance')
    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    overall_bar_chart_image = base64.b64encode(buf.getvalue()).decode('utf-8')

    # Prepare data for subject-wise performance
    subjects = Subject.query.all()
    subject_performance = {}

    for subject in subjects:
        subject_quiz_results = QuizResult.query.join(Quiz).join(Chapter).filter(Chapter.subject_id == subject.id, QuizResult.user_id == user_id).all()
        subject_scores = [result.score for result in subject_quiz_results]
        subject_performance[subject.subject] = sum(subject_scores) / len(subject_scores) if subject_scores else 0

    # Generate bar chart for subject-wise performance
    plt.figure(figsize=(10, 5))
    plt.bar(subject_performance.keys(), subject_performance.values(), color='green')
    plt.xlabel('Subjects')
    plt.ylabel('Average Scores')
    plt.title(f'{user.fullname}\'s Subject-wise Performance')
    plt.xticks(rotation=45)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    subject_bar_chart_image = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render_template(
        'user_performance.html',
        user=user,
        overall_bar_chart_image=overall_bar_chart_image,
        subject_bar_chart_image=subject_bar_chart_image
    )

@app.route("/overall_performance")
def overall_performance():
    # Fetch all subjects
    subjects = Subject.query.all()

    # Prepare data for subject-wise performance
    subject_avg_scores = {}
    subject_quiz_counts = {}

    for subject in subjects:
        # Fetch all quizzes for the subject
        quizzes = Quiz.query.join(Chapter).filter(Chapter.subject_id == subject.id).all()

        # Fetch all results for these quizzes
        quiz_ids = [quiz.id for quiz in quizzes]
        results = QuizResult.query.filter(QuizResult.quiz_id.in_(quiz_ids)).all()

        # Calculate average score for the subject
        if results:
            subject_avg_scores[subject.subject] = sum(result.score for result in results) / len(results)
        else:
            subject_avg_scores[subject.subject] = 0

        # Count the number of quizzes attempted in the subject
        subject_quiz_counts[subject.subject] = len(results)

    # Generate bar chart for average scores by subject
    plt.figure(figsize=(12, 6))
    plt.bar(subject_avg_scores.keys(), subject_avg_scores.values(), color='blue')
    plt.xlabel('Subjects')
    plt.ylabel('Average Score')
    plt.title('Overall Student Performance by Subject')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save the bar chart to a BytesIO object
    buf1 = io.BytesIO()
    plt.savefig(buf1, format='png')
    buf1.seek(0)
    plt.close()

    # Encode the bar chart image to base64
    avg_score_chart_image = base64.b64encode(buf1.getvalue()).decode('utf-8')

    # Generate bar chart for quiz attempts by subject (interest)
    plt.figure(figsize=(12, 6))
    plt.bar(subject_quiz_counts.keys(), subject_quiz_counts.values(), color='green')
    plt.xlabel('Subjects')
    plt.ylabel('Number of Quiz Attempts')
    plt.title('Student Interest by Subject (Quiz Attempts)')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save the bar chart to a BytesIO object
    buf2 = io.BytesIO()
    plt.savefig(buf2, format='png')
    buf2.seek(0)
    plt.close()

    # Encode the bar chart image to base64
    quiz_attempts_chart_image = base64.b64encode(buf2.getvalue()).decode('utf-8')

    return render_template(
        "overall_performance.html",
        avg_score_chart_image=avg_score_chart_image,
        quiz_attempts_chart_image=quiz_attempts_chart_image
    )

@app.route("/students_details")
def students_details():
    students = User_Info.query.filter(User_Info.role != 0).all()
    admin_name = session.get("user_name")  
    admin_info = User_Info.query.get(admin_name)  
    
    return render_template("students_details.html", students=students, user_info=admin_info)

# Remove the separate update_profile route and modify view_profile to handle updates:

# In controller.py - modify view_profile route
@app.route("/view_profile/<int:user_id>", methods=["GET", "POST"])
@login_required
def view_profile(user_id):
    # Authorization check
    if user_id != session.get('user_id') and session.get('role') != 0:
        flash("You can only edit your own profile", "error")
        return redirect(url_for('user_interface', id=session.get('user_id')))

    user_info = User_Info.query.get_or_404(user_id)

    if request.method == "POST":
        try:
            # Update profile fields
            user_info.fullname = request.form.get('fullname', user_info.fullname)
            user_info.email = request.form.get('email', user_info.email)
            user_info.qualification = request.form.get('qualification', user_info.qualification)
            
            # Handle date of birth
            dob_str = request.form.get('dob')
            if dob_str:
                try:
                    user_info.dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                except ValueError:
                    flash("Invalid date format. Please use YYYY-MM-DD.", "error")
            
            db.session.commit()
            flash("Profile updated successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating profile: {str(e)}", "error")
        
        return redirect(url_for('view_profile', user_id=user_id))

    return render_template("view_profile.html", user_info=user_info)


# Route to delete a chapter
@app.route("/delete_chapter/<int:chapter_id>", methods=["POST"])
def delete_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    subject_id = chapter.subject_id
    
    try:
        # Delete all content files first
        contents = content.query.filter_by(chapter_id=chapter_id).all()
        for content_item in contents:
            try:
                if os.path.exists(content_item.file_path):
                    os.remove(content_item.file_path)
            except Exception as e:
                app.logger.error(f"Error deleting file {content_item.file_path}: {str(e)}")
        
        # Delete all quizzes and related data
        quizzes = Quiz.query.filter_by(chapter_id=chapter_id).all()
        for quiz in quizzes:
            # Delete quiz results
            QuizResult.query.filter_by(quiz_id=quiz.id).delete()
            # Delete user answers
            UserAnswers.query.filter_by(quiz_id=quiz.id).delete()
            # Delete questions
            Question.query.filter_by(quiz_id=quiz.id).delete()
            db.session.delete(quiz)
        
        # Delete the chapter and its content
        content.query.filter_by(chapter_id=chapter_id).delete()
        db.session.delete(chapter)
        db.session.commit()
        
        flash("Chapter and all its content deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting chapter: {str(e)}", "error")
    
    return redirect(url_for("admin_dashboard", Name=session.get('user_name', 'Admin')))

@app.route("/delete_subject/<int:subject_id>", methods=["POST"])
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    try:
        # Get all chapters for this subject
        chapters = Chapter.query.filter_by(subject_id=subject_id).all()
        
        for chapter in chapters:
            # Delete all content files first
            contents = content.query.filter_by(chapter_id=chapter.id).all()
            for content_item in contents:
                try:
                    if os.path.exists(content_item.file_path):
                        os.remove(content_item.file_path)
                except Exception as e:
                    app.logger.error(f"Error deleting file {content_item.file_path}: {str(e)}")
            
            # Delete all quizzes and related data for each chapter
            quizzes = Quiz.query.filter_by(chapter_id=chapter.id).all()
            for quiz in quizzes:
                # Delete quiz results
                QuizResult.query.filter_by(quiz_id=quiz.id).delete()
                # Delete user answers
                UserAnswers.query.filter_by(quiz_id=quiz.id).delete()
                # Delete questions
                Question.query.filter_by(quiz_id=quiz.id).delete()
                db.session.delete(quiz)
            
            # Delete chapter content
            content.query.filter_by(chapter_id=chapter.id).delete()
            db.session.delete(chapter)
        
        # Finally delete the subject
        db.session.delete(subject)
        db.session.commit()
        
        flash("Subject and all its content deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting subject: {str(e)}", "error")
    
    return redirect(url_for("admin_dashboard", Name=session.get('user_name', 'Admin')))


@app.route('/quiz_summary/<int:quiz_id>')
def quiz_summary(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if quiz.deadline > datetime.utcnow():
        flash("Quiz still active. Summary not available.", "warning")
        return redirect(url_for('view_lesson', chapter_id=quiz.chapter_id))
    # Logic to compile and display quiz result
    return render_template('quiz_summary.html', quiz=quiz, answers=quiz.answers)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)