
from flask import Flask, render_template, request,redirect,url_for,flash,session,send_from_directory
from .model import *
from datetime import datetime, timedelta
from flask import current_app as app
import os
from werkzeug.utils import secure_filename
from functools import wraps


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("user_name")
        password = request.form.get("password")
        user = User_Info.query.filter_by(email=username, password=password).first()
        if user and user.role==0:
           
           return redirect(url_for("admin_dashboard",Name=username))
        elif user and user.role==1:
            return redirect(url_for("user_interface",name=username))
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
    subjects = get_subjects()
    chapters = get_chapters()
    quizzes = Quiz.query.all()
    contents = content.query.all()
    return render_template("admin_dashboard.html",Name=Name, subjects=subjects,chapters=chapters,quizzes=quizzes, content=contents)

@app.route("/user/<id>")
def user_interface(id):
    subjects = get_subjects()
    chapters = get_chapters()
    user_info = User_Info.query.filter_by(id=id).first()
    return render_template("user_interface.html",id=id, subjects=subjects,chapters=chapters,now=datetime.now(),user_info = user_info)



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


@app.route("/add_chapter/<int:subject_id>", methods=["GET","POST"])
def add_chapter(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    if request.method == "POST":
        chapter_name = request.form.get("chapter_name")
        chapter_description = request.form.get("chapter_description")
        new_chapter = Chapter(chapter=chapter_name, description=chapter_description, subject_id=subject_id)
        db.session.add(new_chapter)
        db.session.commit()

        for content_type in['video','pdf','ppt','doc']:

            if content_type in request.files:
                file = request.files[content_type]
                if file and allowed_file(file.filename, content_type):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(upload_folder, str(new_chapter.id), content_type, filename)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    file.save(file_path)
                    new_content = content(title=filename, content_type=content_type, chapter_id=new_chapter.id,file_path=file_path)
                    db.session.add(new_content)
                    try:
                        db.session.commit()
                        flash(f'{content_type.capitalize()} content uploaded successfully!', 'success')
                    except Exception as e:
                        db.session.rollback()
                        flash(f'Error uploading {content_type} content: {str(e)}', 'error')

        return redirect(url_for("admin_dashboard",subject_id=subject_id,Name="Admin"))
    return render_template("add_chapter.html", subject=subject)

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
    existing_question=0
    existing_question = Question.query.filter_by(quiz_id=quiz_id, question=request.form.get('question')).first()
    if existing_question and existing_question >= quiz.totalNoQues:
        flash("All questions added limit attained ", "success")
        return redirect(url_for('admin_dashboard', Name=session.get('user_name', '')))
    existing_question=1
    remaining_questions = quiz.totalNoQues - existing_question
    return render_template('add_questions.html', quiz=quiz, question_type=type, remaining_questions=remaining_questions)

@app.route("/save_question/<int:quiz_id>", methods=["POST","GET"])
def save_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == "POST":
        try:
            question_type = request.form.get('question_type')
            question = request.form.get('question')
            marks = int(request.form.get('marks'))

            if not all([question_type, question, marks]):
                flash("Question text and Marks are required", "error")
                return redirect(url_for('add_questions', quiz_id=quiz_id, type=question_type))
            
            # Create new question with common fields
            new_question = Question(
                question_text=question,
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
                correct = request.form.get('correct')
            # Handle specific question type fields
                new_question.option1 = option1
                new_question.option2 = option2
                new_question.option3 = option3
                new_question.option4 = option4
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
            if existing_questions >= quiz.totalNoQues:
                flash('All questions have been added!', 'success')
                return redirect(url_for('admin_dashboard', Name=session.get('user_name', '')))
            
            if 'add_another' in request.form:
                flash('Question saved successfully! Add another.', 'success')
                return redirect(url_for('add_questions', quiz_id=quiz_id, type=question_type))
            
            return redirect(url_for('admin_dashboard', Name=session.get('user_name', '')))
                            
            
        except ValueError as e:
            flash(f'Invalid numeric value: {str(e)}', 'error')
            return redirect(url_for('add_questions', quiz_id=quiz_id, type=question_type))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('add_questions', quiz_id=quiz_id, type=question_type))
    
def get_subjects():
    allsubject = Subject.query.all()
    return allsubject

def get_chapters():
    allchapter = Chapter.query.all()
    return allchapter

@app.route("/start_quiz/<int:quiz_id>", methods=["GET"])
def start_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    if datetime.now() > quiz.deadline:
        flash('Quiz deadline has passed "QUIZ EXPIRED"', 'error')
        return redirect(url_for('user_interface',id=id))
    
    if QuizResult.query.filter_by(user_id=session['user_info.id'],quiz_id=quiz_id).first():
        flash('You have already attempted this quiz', 'error')
        return redirect(url_for('user_interface'))
    return render_template('start_quiz.html', quiz=quiz)

@app.route("/attempt_quiz/<int:quiz_id>" , methods=["POST","GET"])
def attempt_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    if request.method == "POST":
        session['quiz_start_time']=datetime.now().timestamp()
        session['quiz_id']=quiz_id
        session['quiz_answers']={}

        return render_template("attempt_quiz.html",quiz=quiz, current_question=0, start_time=session['quiz_start_time'])
    if 'quiz_start_time' not in session or session['quiz_id'] != quiz_id:
        return redirect(url_for('start_quiz', quiz_id=quiz_id))
    
    time_spent = datetime.now().timestamp()-session['quiz_start_time']
    remaining_time = max(0, quiz.duration * 60 - time_spent)
    
    if remaining_time <= 0:
        return submit_quiz(quiz_id)
    return render_template('attempt_quiz.html', quiz=quiz, remaining_time=remaining_time)

@app.route("/submit_quiz/<int:quiz_id>", methods=["POST"])
def submit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    start_time = datetime.fromtimestamp(session['quiz_start_time'])
    end_time = datetime.now()
    time_taken = end_time - start_time

    answer =  {}
    score = 0

    for question in quiz.questions:
        answer_key = f"q{question.id}"
        selected_answer = request.form.get(answer_key)
        if selected_answer:
            answer[question_id] = int(selected_answer)
            option = Question.query.get(int(selected_answer))
            if option and option.correct:
                score += question.marks
    
    quiz_result = QuizResult(
        user_id=session['user_id'],
        quiz_id=quiz_id,
        score=score,
        date_taken=start_time
    )
    db.session.add(quiz_result)
    for question_id, option_id in answer.items():
        user_answer =UserAnswers(quiz_res_id=quiz_result.id, question_id=question_id, option_selected=option_id)
        db.session.add(user_answer)
    db.session.commit()
    
    session.pop('quiz_start_time',None)
    session.pop('quiz_id',None)
    session.pop('quiz_answers',None)
    
    return redirect(url_for('quiz_result',result_id=quiz_result.id))

@app.route("/quiz_result/<int:result_id>")
def quiz_result(result_id):
    result = QuizResult.query.get_or_404(result_id)
    return render_template('quiz_result.html', result=result)

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

# @app.route('/upload_pdf', methods=['POST'])
# def upload_content(chapter_id):
#     if not current_user.is_admin:
#         flash('Access denied', 'error')
#         return redirect(url_for('index'))

#     if request.method == 'POST':
#         if 'file' not in request.files:
#             flash('No file selected', 'error')
#             return redirect(request.url)

#         file = request.files['file']
#         title = request.form.get('title')
#         content_type = request.form.get('content_type')

#         if file.filename == '':
#             flash('No file selected', 'error')
#             return redirect(request.url)

#         if file and allowed_file(file.filename):
#             try:
#                 filename = secure_filename(file.filename)
#                 # Create directory if it doesn't exist
#                 os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                
#                 # Save file
#                 file_path = os.path.join('uploads', filename)
#                 file.save(os.path.join('Quiz_Master_website/static', file_path))

#                 # Save to database
#                 new_content = Content(
#                     title=title,
#                     file_path=file_path,
#                     content_type=content_type,
#                     chapter_id=chapter_id
#                 )
#                 db.session.add(new_content)
#                 db.session.commit()

#                 flash('Content uploaded successfully!', 'success')
#                 return redirect(url_for('view_chapter', chapter_id=chapter_id))
            
#             except Exception as e:
#                 db.session.rollback()
#                 flash(f'Error uploading content: {str(e)}', 'error')
#                 return redirect(request.url)

#     chapter = Chapter.query.get_or_404(chapter_id)
#     return render_template('view_chapter.html', chapter=chapter)
@app.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)



if __name__ == "__main__":
    app.run(debug=True)