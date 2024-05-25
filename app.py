from flask import Flask, render_template, request, redirect, url_for
import os
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
import random
from collections import defaultdict
import math
from itertools import combinations

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}

def calculate_current_cgpa(student_df):
    studentScore = 0  # Initialize total score
    total_credits_passed = 0  # Initialize total credits of passed courses
    # student_df = pd.read_csv('dataset/allstudentdata/' + student_id + '.csv')
    print(student_df, 'student_df')
    sems = student_df['Semester Offer'].unique()

    # Initialize student score and total credits passed if not already initialized
    studentScore = 0
    total_credits_passed = 0
    course_latest_info = {}
    # Loop through each semester
    passed_courses = set()
    warning_count = 0
    for sm in sems:
        sem = student_df[student_df['Semester Offer'] == sm]
        
        # Get the GPA, CreditHour, and CourseID data for the semester
        data = sem[['GPA', 'CreditHour', 'CourseID']].values.tolist()
        
        # Calculate SGPA for the semester
        score = sum([x * b for x, b, _ in data])
        credits_count = sum([b for _, b, _ in data])
        SGPA = score / credits_count

        for x, b, course_id in data:
            course_latest_info[course_id] = (x, b)
        # Calculate total credits passed (excluding failed courses)
        # cgpaSCore = 
        # credits_passed = 0
        # for x, b, course_id in data:
        #     if course_id not in passed_courses:
        #         credits_passed += b
        #         passed_courses.add(course_id)
        
        # # Update total score and total credits passed
        # studentScore += score
        # total_credits_passed += credits_passed
        
        # # Calculate CGPA
        # CGPA = studentScore / total_credits_passed 
        # loop through course_latest_info and calculate the total score and total credits passed for the student
        studentScore = 0
        total_credits_passed = 0
        for course_id, (x, b) in course_latest_info.items():
            studentScore += x * b
            total_credits_passed += b

        CGPA = studentScore / total_credits_passed
        if CGPA < 2:
            warning_count +=1
        else:
            warning_count = 0
    print(CGPA, 'cgpa')
    return [CGPA, warning_count]

class Student:
    def __init__(self, student_id, level_of_understanding, preferences, warning_status, cgpa, current_semester):
        self.student_id = student_id
        self.level_of_understanding = level_of_understanding
        self.preferences = preferences
        self.warning_status = warning_status
        self.cgpa = cgpa
        self.current_semester = current_semester

class Course:
    def __init__(self, course_id, name, category, chain_courses, grade, semester_offer, credit_hours, repeat_status):
        self.course_id = course_id
        self.name = name
        self.category = category
        self.chain_courses = chain_courses
        self.grade = grade
        self.semester_offer = semester_offer
        self.credit_hours = credit_hours
        self.repeat_status = repeat_status

class Transcript:
    def __init__(self, student_id, courses_taken):
        self.student_id = student_id
        self.courses_taken = courses_taken  # List of Course objects

def load_data():
    student_df = pd.read_csv('dataset/Students.csv')
    course_df = pd.read_csv('dataset/courses.csv')
    return student_df, course_df

# def categorize_students(student):
#     if student.cgpa >= 1.85:
#         return 'near_2.0'
#     elif student.cgpa >= 1.5:
#         return 'near_1.5'
#     else:
#         return 'less_than_1.5'

# def classify_student_type(transcript):
#     grades = [course.grade for course in transcript.courses_taken]
#     if sum(grades) / len(grades) > 2.5:
#         return 'good'
#     elif sum(grades) / len(grades) > 1.5:
#         return 'average'
#     else:
#         return 'below_average'

def get_courses_taken(student_id, transcripts):
    for transcript in transcripts:
        if transcript.student_id == student_id:
            return transcript.courses_taken
    return []

def calculate_gpa(courses_taken):
    
    total_points = 0
    total_credits = 0
    for course in courses_taken:
        total_points += course.grade * course.credit_hours
        total_credits += course.credit_hours
    return total_points / total_credits

def calculate_category_weights(transcript):
    category_gpa_sum = defaultdict(float)
    category_course_count = defaultdict(int)

    # Calculate the sum of GPAs and count of courses for each category
    for course in transcript.courses_taken:
        if not math.isnan(course.grade):
            category_gpa_sum[course.category] += course.grade
            category_course_count[course.category] += 1
    
    # Calculate the average GPA for each category
    category_avg_gpa = {}
    for category, gpa_sum in category_gpa_sum.items():
        course_count = category_course_count[category]
        if course_count > 0:
            category_avg_gpa[category] = gpa_sum / course_count
        else:
            category_avg_gpa[category] = 0.0
    
    # Normalize the average GPAs to get weights
    total_avg_gpa = sum(category_avg_gpa.values())
    category_weights = {category: avg_gpa / total_avg_gpa for category, avg_gpa in category_avg_gpa.items()}
    
    return category_weights

def calculate_category_weighted_avg_gpa(transcript, category_weights, threshold, x_factor):
    category_gpa = defaultdict(list)

    # Calculate the sum of grades for each category
    for course in transcript.courses_taken:
        if not math.isnan(course.grade):
            category_gpa[course.category].append(course.grade)
    
    # Calculate the weighted average GPA for each category
    category_weighted_avg_gpa = {}
    for category, grades in category_gpa.items():
        avg_weight = category_weights.get(category, 0.0)
        
        avg_weight += .5 # adding bias
        weighted_avg = sum(grades) / len(grades) * avg_weight
        
        # If the weighted average is below the threshold, add the x_factor
        if weighted_avg < threshold:
            weighted_avg += x_factor

        category_weighted_avg_gpa[category] = weighted_avg
    
    return category_weighted_avg_gpa

def getTranscript(student_id, all_transcripts):
    for transcript in all_transcripts:
        if transcript.student_id == student_id:
            return transcript.courses_taken
    return []

def knowledge_based_filtering(student, available_courses, student_transcript):
    recommendations = []
    taken_courses = student_transcript.courses_taken
    taken_course_ids = [course.course_id for course in taken_courses]

    for course in available_courses:
        score = 0
        if course.category in student.level_of_understanding:
            score += 10
        if course.name in student.preferences:
            score += 5
        if course.course_id in taken_course_ids:
            for taken_course in taken_courses:
                if taken_course.course_id == course.course_id and taken_course.grade < 2.0 and taken_course.credit_hours > 1:
                    score += 30        
        prerequisites_met = all(prerequisite in taken_course_ids for prerequisite in course.chain_courses)
        if prerequisites_met and course.course_id not in taken_course_ids:
            score += 15

        recommendations.append((course, score))
    
    recommendations.sort(key=lambda x: x[1], reverse=True)
    return [(course, score) for course, score in recommendations]

def rank_combinations_by_knowledge(student, combinations, student_transcript):
    ranked_combinations = []
    for combo, new_gpa in combinations:
        total_score = 0
        for course in combo:
            filtered_courses = [course]
            filtered_recommendations = knowledge_based_filtering(student, filtered_courses, student_transcript)
            if filtered_recommendations:
                total_score += filtered_recommendations[0][1]
        ranked_combinations.append((combo, new_gpa, total_score))
    
    ranked_combinations.sort(key=lambda x: x[2], reverse=True)
    return ranked_combinations

def select_top_recommendations(ranked_combinations):
    selected_recommendations = []
    
    five_courses_combos = [combo for combo in ranked_combinations if len(combo[0]) == 5]
    four_courses_combos = [combo for combo in ranked_combinations if len(combo[0]) == 4]
    three_courses_combos = [combo for combo in ranked_combinations if len(combo[0]) == 3]
    two_courses_combos = [combo for combo in ranked_combinations if len(combo[0]) == 2]

    if five_courses_combos:
        selected_recommendations.append(five_courses_combos[0])
    if four_courses_combos:
        selected_recommendations.append(four_courses_combos[0])
    if three_courses_combos:
        selected_recommendations.append(three_courses_combos[0])
    if two_courses_combos:
        selected_recommendations.append(two_courses_combos[0])
    
    # Ensure at least 3 recommendations
    if len(selected_recommendations) < 3:
        all_combos = two_courses_combos[1:] + three_courses_combos[1:] + four_courses_combos[1:] + five_courses_combos[1:]
        for combo in all_combos:
            if len(selected_recommendations) < 3:
                selected_recommendations.append(combo)

    # Ensure unique recommendations
    unique_selected_recommendations = []
    for rec in selected_recommendations:
        if rec not in unique_selected_recommendations:
            unique_selected_recommendations.append(rec)

    return unique_selected_recommendations[:3]  # Ensure only 3 recommendations
def find_combinations_to_clear_warning(student,student_df, available_courses, student_transcript):
    # taken_courses = get_courses_taken(student.student_id, transcripts)
    taken_courses = student_transcript.courses_taken

    # student_transcript = getTranscript(student.student_id, transcripts)
    # Call the function to calculate category weights
    category_weights = calculate_category_weights(student_transcript)

    # Define threshold and x_factor
    threshold = 2   # Example threshold
    x_factor = 1     # Example factor to add if weighted average is below the threshold

    # Call the function for a student's transcript
    category_weighted_avg_gpa = calculate_category_weighted_avg_gpa(student_transcript, category_weights, threshold, x_factor)
                                                                
    # category_avg_gpa = calculate_category_average_gpa(taken_courses)
    
    # stid = f'k{student.student_id[0:2]}{student.student_id.split("-")[1]}'
    
    
    GPA = calculate_current_cgpa(student_df)
    current_gpa = GPA[0]
    warning_count = GPA[1]

    required_gpa = 2.0
    if current_gpa >= required_gpa:
        return []
    successful_combinations = []
    num_courses = len(available_courses)

    print(category_weighted_avg_gpa, 'category_weighted_avg_gpa')

    for r in range(1, num_courses + 1):
        for combo in combinations(available_courses, r):
            new_courses = list(combo)
            for course in new_courses:
                # Estimate GPA for new courses based on category average
                estimated_grade = category_weighted_avg_gpa.get(course.category, 0)
                course.grade = round(estimated_grade, 3)
            # combined_courses = list(set(taken_courses)) + new_courses
            # for combined_course in combined_courses:
            #     print(combined_course.name)
            common_courses = set([course.course_id for course in taken_courses]).intersection([course.course_id for course in new_courses])
            
            # if common courses gpa is less than 3.0, then subtract that course from new_courses
            for common_course in common_courses:
                for course in new_courses:
                    if course.course_id == common_course and course.grade >= 3:
                        
                        new_courses.remove(course)

                
            if len(new_courses) == 0:
                continue
            
            combined_courses = []
            

            filtered_courses = []
            # iterate from last to first in taken courses and make a list of courses that comes first, if there is a duplicate don't add
            for course in taken_courses[::-1]:
                if course.course_id not in [filtered_course.course_id for filtered_course in filtered_courses]:
                    filtered_courses.append(course)


            for course in filtered_courses:
                if course.course_id not in [new_course.course_id for new_course in new_courses]:
                    combined_courses.append(course)

            # now add the new courses
            combined_courses.extend(new_courses)
            # print([(course.name, course.grade) for course in combined_courses], 'combined_courses')
            new_gpa = calculate_gpa(combined_courses)
            
            if new_gpa >= required_gpa:
                # round to 2 decimal places
                new_gpa = round(new_gpa, 2)
                
                successful_combinations.append((new_courses, new_gpa))

    return successful_combinations


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def getAvailableCourses():
    student_df1, course_df = load_data()
    available_courses = []
    total_courses = len(course_df)
    num_random_courses = 10 
    random_indices = [16, 17, 18, 19, 20, 21, 22]

    for index in random_indices:
        row = course_df.iloc[index]
        chain_courses = []
        
        if not row.empty:
            chain_courses = [row['Chain']] if not pd.isnull(row['Chain']) else []
        course = Course(row['CourseID'], row['CourseName'], row['Category'], chain_courses, 0, row['Semester Offer'], row['CreditHours'], 0)
        available_courses.append(course)
    return available_courses

@app.route('/')
def home():
    available_courses = getAvailableCourses()
    course_names = [course.name for course in available_courses]
    return render_template('index.html', course_names=course_names)

@app.route('/process', methods=['POST'])
def process():
    if 'transcript' not in request.files:
        return redirect(request.url)
    file = request.files['transcript']
    if file.filename == '':
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        level_of_understanding = request.form.getlist('level_of_understanding')
        preferences = request.form.getlist('preferences')

        student_id = request.form['student_id']
        student_df = pd.read_csv(filepath)
        gpa = calculate_current_cgpa(student_df)
        cgpa = gpa[0]
        warning_count = gpa[1]
        warning_status = warning_count
        
        current_semester = int(request.form['current_semester'])
        
        # # Load data
        student_df1, course_df = load_data()
    
        student = Student(student_id, None, [], warning_status, cgpa, current_semester)
        courses_taken = []
        for _, st_row in student_df.iterrows():
            course_info = course_df[course_df['CourseID'] == st_row['CourseID']]
            chain_courses = []
            if not course_info.empty:
                course_info = course_info.iloc[0]
                chain_courses = course_info['Chain'] if not pd.isnull(course_info['Chain']) else []
            course_category = course_info['Category']
            course = Course(st_row['CourseID'], st_row['CourseName'], course_category, chain_courses, st_row['GPA'], course_info['Semester Offer'], course_info['CreditHours'], st_row['Repeat Status'])
            courses_taken.append(course)

        student_transcript = Transcript(student_id, courses_taken)
        student.level_of_understanding =level_of_understanding
        student.preferences = preferences

        available_courses = getAvailableCourses()

        successful_combinations = find_combinations_to_clear_warning(student,student_df, available_courses, student_transcript)
        ranked_combinations = rank_combinations_by_knowledge(student, successful_combinations, student_transcript)
        top_recommendations = select_top_recommendations(ranked_combinations)

        return render_template('results.html', student=student, available_courses=available_courses, successful_combinations=top_recommendations)

    return redirect(request.url)

if __name__ == '__main__':
    app.run(debug=True)