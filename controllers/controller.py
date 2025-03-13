
from flask import Flask, render_template, request,redirect,url_for,flash,session,send_from_directory
from .model import *
from datetime import datetime, timedelta
from flask import current_app as app
import os
from werkzeug.utils import secure_filename
from functools import wraps
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import io
import base64


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
def user_interface(id):
    subjects = get_subjects()
    chapters = get_chapters()
    user_info = User_Info.query.filter_by(id=id).first()
    name = user_info.fullname
    quiz_results = {}
    for chapter in chapters:
        for quiz in chapter.quizzes:
            result = QuizResult.query.filter_by(user_id=user_info.id, quiz_id=quiz.id).first()
            quiz_results[quiz.id] = result.id if result else None
    session["quiz_results"] = quiz_results
    return render_template("user_interface.html",id=id, subjects=subjects,chapters=chapters,now=datetime.now(),user_info = user_info,quiz_results=quiz_results,name=name)



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
        chapter_name = request.form.get("chapter_name")
        chapter_description = request.form.get("chapter_description")

        # Check if a chapter with the same name already exists for this subject
        existing_chapter = Chapter.query.filter_by(
            chapter=chapter_name, subject_id=subject_id
        ).first()

        if existing_chapter:
            # If the chapter already exists, use it
            chapter = existing_chapter
            flash("Chapter already exists. Content will be added to the existing chapter.", "info")
        else:
            # If the chapter does not exist, create a new one
            chapter = Chapter(chapter=chapter_name, description=chapter_description, subject_id=subject_id)
            db.session.add(chapter)
            db.session.commit()
            flash("New chapter created successfully!", "success")

        # Handle file uploads for each content type
        content_types = {
            "video": "video",
            "pdf": "pdf",
            "ppt": "ppt",
            "word": "word"
        }

        for content_type, form_key in content_types.items():
            if form_key in request.files:
                file = request.files[form_key]
                if file and allowed_file(file.filename, content_type):
                    filename = secure_filename(file.filename)
                    # Create a directory for the chapter if it doesn't exist
                    chapter_dir = os.path.join(upload_folder, str(chapter.id), content_type)
                    os.makedirs(chapter_dir, exist_ok=True)
                    file_path = os.path.join(chapter_dir, filename)
                    file.save(file_path)

                    # Save content details to the database
                    new_content = content(title=filename,content_type=content_type,chapter_id=chapter.id,file_path=file_path)
                    db.session.add(new_content)
                    try:
                        db.session.commit()
                        flash(f'{content_type.capitalize()} content uploaded successfully!', 'success')
                    except Exception as e:
                        db.session.rollback()
                        flash(f'Error uploading {content_type} content: {str(e)}', 'error')

        return redirect(url_for("admin_dashboard", subject_id=subject_id, Name="Admin"))
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
            # if "add_another" in request.form and remaining_questions > 0 :
            #     flash('All questions have been added!', 'success')
            #     return redirect(url_for('admin_dashboard', Name=session.get('user_name', '')))
            
            # if 'add_another' in request.form:
            #     flash('Question saved successfully! Add another.', 'success')
            #     return redirect(url_for('add_questions', quiz_id=quiz_id, type=question_type))
            
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
    user_id = session.get("user_id")
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()

    if datetime.now() > quiz.deadline:
        flash('Quiz deadline has passed "QUIZ EXPIRED"', 'error')
        return redirect(url_for('user_interface',id=session.get("user_id")))
    
    if QuizResult.query.filter_by(user_id=session.get('user_info.id'),quiz_id=quiz_id).first():
        flash('You have already attempted this quiz', 'error')
        return redirect(url_for('user_interface', id=session.get("user_id")))
    return render_template('start_quiz.html', quiz=quiz,questions=questions)

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
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    user_id = session.get("user_id")

    # Ensure user has started the quiz
    if 'quiz_start_time' not in session:
        flash("Error: No active quiz session found.", "error")
        return redirect(url_for("user_interface", id=user_id))

    start_time = datetime.fromtimestamp(session['quiz_start_time'])
    end_time = datetime.now()
    time_taken = (end_time - start_time).total_seconds()  # Store time in seconds

    score = 0
    answers = {}

    for question in questions:
        question_id = str(question.id)
        answer_key = f"q{question_id}"
        selected_answer = request.form.get(answer_key)
        

        if selected_answer:
            is_correct = False
            
            if question.question_type == "numeric":
                try:
                    selected_answer = float(selected_answer)  
                    correct_answer = float(question.numeric_answer)
                    tolerance = float(question.tolerance) if question.tolerance else 0.0
                    if selected_answer == tolerance:
                        is_correct = True
                        score += question.marks
                    numeric_answer = selected_answer
                except ValueError:
                    flash(f"Invalid numeric input for question {question_id}", "error")
                    return redirect(url_for("start_quiz", quiz_id=quiz_id))
            else:  
                correct_answer_letter = question.correct
                if correct_answer_letter == 'A':
                    correct_answer = question.option1
                elif correct_answer_letter == 'B':
                    correct_answer = question.option2
                elif correct_answer_letter == 'C':
                    correct_answer = question.option3
                elif correct_answer_letter == 'D':
                    correct_answer = question.option4
                else:
                    correct_answer = None
                if selected_answer == correct_answer:
                    is_correct = True
                    score += question.marks

            answers[question_id] = selected_answer  

        
           
            user_answer = UserAnswers(
                user_id=user_id,
                quiz_id=quiz_id,
                question_id=question_id,
                selected_answer=selected_answer if question.question_type != "numeric" else None,  
                numeric_answer=numeric_answer if question.question_type == "numeric" else None ,    
                is_correct=is_correct
            )
            db.session.add(user_answer)
    quiz_result = QuizResult(
        user_id=user_id,
        quiz_id=quiz_id,
        score=score,
        date_taken=start_time,
        time_taken=time_taken
    )
    db.session.add(quiz_result)

    db.session.commit()

    if "quiz_results" not in session:
        session["quiz_results"] = {}
    session["quiz_results"][quiz_id] = quiz_result.id
    
    session.pop('quiz_start_time', None)
    session.pop('quiz_id', None)

    
    return redirect(url_for('quiz_result', result_id=quiz_result.id))


@app.route("/quiz_result/<int:result_id>")
def quiz_result(result_id):
    result = QuizResult.query.get_or_404(result_id)
    quiz = Quiz.query.filter_by(id=result.quiz_id).first()
    user_answers = UserAnswers.query.filter_by(user_id=result.user_id, quiz_id=result.quiz_id).all()
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
    
    return render_template('result.html', result=result, quiz=quiz, question_details=question_details)
    

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


@app.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route("/scores/<int:user_id>")
def scores(user_id):
    user_results = QuizResult.query.filter_by(user_id=user_id).all()
    user_info = User_Info.query.filter_by(id=user_id).first()
    return render_template("scores.html", user_results=user_results, user_info=user_info)



@app.route("/summary/<int:user_id>")
def summary(user_id):
    # Fetch user information
    user_info = User_Info.query.filter_by(id=user_id).first()

    # Fetch all quiz results for the user
    user_results = QuizResult.query.filter_by(user_id=user_id).all()

    # Prepare data for subject-wise performance
    subject_scores = {}
    for result in user_results:
        subject_name = result.quiz.chapter_ref.subject_ref.subject  # Access subject name
        if subject_name not in subject_scores:
            subject_scores[subject_name] = []
        subject_scores[subject_name].append(result.score)

    # Calculate average score for each subject
    subject_avg_scores = {subject: sum(scores) / len(scores) for subject, scores in subject_scores.items()}

    # Fetch all quizzes in the system
    all_quizzes = Quiz.query.all()

    # Determine completed quizzes by the user
    completed_quiz_ids = {result.quiz_id for result in user_results}

    # Calculate incomplete quizzes (including expired quizzes)
    incomplete_quizzes = 0
    for quiz in all_quizzes:
        if quiz.id not in completed_quiz_ids:
            # Check if the quiz has expired
            if quiz.deadline and quiz.deadline < datetime.now():
                incomplete_quizzes += 1

    # Total quizzes in the system
    total_quizzes = len(all_quizzes)

    # Ensure completed quizzes count is accurate
    completed_quizzes = len(completed_quiz_ids)

    # Generate subject-wise performance bar chart
    plt.figure(figsize=(10, 5))
    plt.bar(subject_avg_scores.keys(), subject_avg_scores.values(), color='blue')
    plt.xlabel('Subjects')
    plt.ylabel('Average Score')
    plt.title(f'{user_info.fullname}\'s Subject-wise Performance')
    plt.xticks(rotation=45)
    plt.tight_layout()

    # Save the bar chart to a BytesIO object
    buf1 = io.BytesIO()
    plt.savefig(buf1, format='png')
    buf1.seek(0)
    plt.close()

    # Encode the bar chart image to base64
    bar_chart_image = base64.b64encode(buf1.getvalue()).decode('utf-8')

    # Generate overall quiz completion pie chart
    plt.figure(figsize=(5, 5))
    labels = ['Completed Quizzes', 'Incomplete Quizzes']
    sizes = [completed_quizzes, incomplete_quizzes]
    colors = ['green', 'red']
    plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    plt.title(f'{user_info.fullname}\'s Overall Quiz Completion')
    plt.tight_layout()

    # Save the pie chart to a BytesIO object
    buf2 = io.BytesIO()
    plt.savefig(buf2, format='png')
    buf2.seek(0)
    plt.close()

    # Encode the pie chart image to base64
    pie_chart_image = base64.b64encode(buf2.getvalue()).decode('utf-8')

    return render_template(
        "summary.html",
        bar_chart_image=bar_chart_image,
        pie_chart_image=pie_chart_image,
        user_info=user_info
    )

@app.route("/search")
def search():
    query = request.args.get('query', '').strip()  # Get the search term from the query parameters
    if not query:
        flash("Please enter a search term.", "error")
        return redirect(url_for('admin_dashboard', Name=session.get('user_name', 'Admin')))

    # Search for subjects, chapters, quizzes, or users that start with the query term
    subjects = Subject.query.filter(Subject.subject.ilike(f'%{query}%')).all()
    chapters = Chapter.query.filter(Chapter.chapter.ilike(f'%{query}%')).all()
    quizzes = Quiz.query.filter(Quiz.title.ilike(f'%{query}%')).all()
    users = User_Info.query.filter(User_Info.fullname.ilike(f'%{query}%')).all()

    return render_template('search.html', query=query, subjects=subjects, chapters=chapters, quizzes=quizzes, users=users)

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

@app.route("/view_profile/<int:user_id>", methods=["GET", "POST"])
def view_profile(user_id):
    # Fetch the user's details
    user_info = User_Info.query.get_or_404(user_id)

    if request.method == "POST":
        # Update the user's details
        user_info.fullname = request.form.get("fullname", user_info.fullname)
        user_info.email = request.form.get("email", user_info.email)
        user_info.qualification = request.form.get("qualification", user_info.qualification)
        user_info.dob = request.form.get("dob", user_info.dob)

        # Save changes to the database
        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("view_profile", user_id=user_id))

    return render_template("view_profile.html", user_info=user_info)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)