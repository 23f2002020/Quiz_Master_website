from flask_restful import Resource, Api
from flask import request
from .model import db, Quiz, Chapter  
from datetime import datetime

api = Api()

class QuizAPI(Resource):
    
    def get(self):
        quizzes = Quiz.query.all()
        quizzes_json = []
        for quiz in quizzes:
            quizzes_json.append({
                'id': quiz.id,
                'title': quiz.title,
                'description': quiz.description,
                'chapter_id': quiz.chapter_id,
                'deadline': str(quiz.deadline),
                'duration': quiz.duration,
                'total_marks': quiz.totalMarks,
                'passing_marks': quiz.passingMarks,
                'total_questions': quiz.totalNoQues
            })
        return quizzes_json

    def post(self):
        title = request.json.get("title")
        description = request.json.get("description")
        chapter_id = request.json.get("chapter_id")
        deadline = request.json.get("deadline")
        duration = request.json.get("duration")
        total_marks = request.json.get("total_marks")
        passing_marks = request.json.get("passing_marks")
        total_questions = request.json.get("total_questions")

        chapter = Chapter.query.get(chapter_id)
        if not chapter:
            return {"message": "Chapter not found"}, 404

        try:
            deadline_dt = datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return {"message": "Invalid deadline format. Use YYYY-MM-Dd %H:%M:%S"}, 400

        new_quiz = Quiz(
            title=title,
            description=description,
            chapter_id=chapter_id,
            deadline=deadline_dt,
            duration=duration,
            totalMarks=total_marks,
            passingMarks=passing_marks,
            totalNoQues=total_questions
        )
        db.session.add(new_quiz)
        db.session.commit()

        return {"message": "Quiz created successfully!", "quiz_id": new_quiz.id}, 201

    def put(self, id):
        quiz = Quiz.query.filter_by(id=id).first()
        if quiz:
            quiz.title = request.json.get("title", quiz.title)
            quiz.description = request.json.get("description", quiz.description)
            quiz.chapter_id = request.json.get("chapter_id", quiz.chapter_id)
            quiz.duration = request.json.get("duration", quiz.duration)
            quiz.totalMarks = request.json.get("total_marks", quiz.totalMarks)
            quiz.passingMarks = request.json.get("passing_marks", quiz.passingMarks)
            quiz.totalNoQues = request.json.get("total_questions", quiz.totalNoQues)

            
            deadline = request.json.get("deadline")
            if deadline:
                try:
                    quiz.deadline = datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    return {"message": "Invalid deadline format. Use YYYY-MM-%d %H:%M:%S"}, 400

            db.session.commit()
            return {"message": "Quiz updated successfully!"}, 200

        return {"message": "Quiz not found!"}, 404

    def delete(self, id):
        quiz = Quiz.query.filter_by(id=id).first()
        if quiz:
            db.session.delete(quiz)
            db.session.commit()
            return {"message": "Quiz deleted successfully!"}, 200

        return {"message": "Quiz not found!"}, 404

class QuizSearchAPI(Resource):
    def get(self, id):
        quiz = Quiz.query.filter_by(id=id).first()
        if quiz:
            quiz_json = {
                'id': quiz.id,
                'title': quiz.title,
                'description': quiz.description,
                'chapter_id': quiz.chapter_id,
                'deadline': str(quiz.deadline),
                'duration': quiz.duration,
                'total_marks': quiz.totalMarks,
                'passing_marks': quiz.passingMarks,
                'total_questions': quiz.totalNoQues
            }
            return quiz_json, 200

        return {"message": "Quiz not found!"}, 404


api.add_resource(QuizAPI, "/api/quizzes", "/api/quizzes/<int:id>")
api.add_resource(QuizSearchAPI, "/api/quizzes/search/<int:id>")