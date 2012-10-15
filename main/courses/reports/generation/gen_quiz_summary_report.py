from c2g.models import *
from courses.reports.generation.C2GReportWriter import *
from courses.reports.generation.get_quiz_data import *
import math

mean = lambda k: sum(k)/len(k)

def gen_course_quizzes_report(ready_course, save_to_s3=False):
    
    ### 1- Compose the report file name and instantiate the report writer object
    dt = datetime.now()
    course_prefix = ready_course.handle.split('--')[0]
    course_suffix = ready_course.handle.split('--')[1]
    
    report_name = "%02d_%02d_%02d__%02d_%02d_%02d-%s-Course-Quizzes.csv" % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, course_prefix+'_'+course_suffix)
    s3_filepath = "%s/%s/reports/course_quizzes/%s" % (course_prefix, course_suffix, report_name)
    
    rw = C2GReportWriter(save_to_s3, s3_filepath)
    
    ### 2- Write the Report Title
    rw.write(content = ["Course Quizzes for %s (%s %d)" % (ready_course.title, ready_course.term.title(), ready_course.year)], nl = 1)
    
    ### 3- Get a list of Quizzes (Problem sets and videos with exercises) to Add theit Report Content
    quizzes = []
    problemsets = ProblemSet.objects.getByCourse(course=ready_course)
    for ps in problemsets:
        quizzes.append(ps)
        
    videos = Video.objects.getByCourse(course=ready_course)
    for vd in videos:
        quizzes.append(vd)
        
    quizzes = sorted(quizzes, key=lambda k:k.live_datetime, reverse=True)
    
    ### 4- Write out the report content for each quiz
    for q in quizzes:
        WriteQuizSummaryReportContent(q, rw, full=False)

    ### 5- Proceed to write out and return
    report_content = rw.writeout()
    return {'name': report_name, 'content': report_content, 'path': s3_filepath}

def gen_quiz_summary_report(ready_course, ready_quiz, save_to_s3=False):
    
    ### 1- Create the S3 file name and report writer object
    dt = datetime.now()
    course_prefix = ready_course.handle.split('--')[0]
    course_suffix = ready_course.handle.split('--')[1]
    is_video = isinstance(ready_quiz, Video)
    is_summative = (not is_video) and (ready_quiz.assessment_type == 'assessive')
    
    report_name = "%02d_%02d_%02d__%02d_%02d_%02d-%s.csv" % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, ready_quiz.slug)
    if is_video:
        s3_filepath = "%s/%s/reports/videos_summary/%s" % (course_prefix, course_suffix, report_name)
    else:
        s3_filepath = "%s/%s/reports/problemsets_summary/%s" % (course_prefix, course_suffix, report_name)
    
    rw = C2GReportWriter(save_to_s3, s3_filepath)
    
    ### 2- Get the quiz data
    quiz_data = get_quiz_data(ready_quiz)
    per_student_data = quiz_data['per_student_data']
    exercise_summaries = quiz_data['exercise_summaries']
    
    ### 4- Write out the report content
    WriteQuizSummaryReportContent(ready_quiz, rw, full=False)

    ### 5- Proceed to write out and return
    report_content = rw.writeout()
    return {'name': report_name, 'content': report_content, 'path': s3_filepath}


def WriteQuizSummaryReportContent(ready_quiz, rw, full=False):
    ### 1- Get the quiz data
    quiz_data = get_quiz_data(ready_quiz)
    quiz_summary = quiz_data['quiz_summary']
    exercise_summaries = quiz_data['exercise_summaries']
    
    ### 2- Write the title line
    rw.write([quiz_summary['title']])
    
    ### 3- Write out per-exercise report content
    if len(exercise_summaries) == 0:
        rw.write(content = ["No exercises have been added yet."], indent = 1, nl = 1)
        return
    
    
    if quiz_summary['assessment_type'] == 'summative':
        if len(quiz_summary['scores']) > 0:
            rw.write(["Mean score", mean(quiz_summary['scores']), "Max score", max(quiz_summary['scores']), "", "Mean score after late penalty", mean(quiz_summary['scores_after_late_penalty']), "Max score after late penalty", max(quiz_summary['scores_after_late_penalty'])], indent = 1, nl = 1)
        
    
    content = ["Exercise"]
    if quiz_summary['assessment_type'] == 'summative': content.extend(["Mean score", "Max score"])
    content.extend(["Total attempts", "Students who have attempted", "Correct attempts", "Correct 1st attempts", "Correct 2nd attempts", "Correct 3rd attempts", "Median attempts to (and including) first correct attempt", "Median attempt time", "Most freq incorrect answer"])
    rw.write(content, indent = 1)
    
    for ex_id in exercise_summaries:
        ex_summary = exercise_summaries[ex_id]
        
        content = [ex_summary['slug']]
        if quiz_summary['assessment_type'] == 'summative': content.extend([mean(ex_summary['scores']), max(ex_summary['scores'])])
        
        most_freq_incorrect_answer_str = "Too few, or no high freq, incorrect attempts"
        if len(ex_summary['most_frequent_incorrect_answers']) > 0:
            most_freq_incorrect_answer_str = "%s (%.2f%% of all incorrect attempts)" % (ex_summary['most_frequent_incorrect_answers'][0][0], ex_summary['most_frequent_incorrect_answers'][0][1])
        content.extend([ex_summary['num_attempts'], ex_summary['num_attempting_students'], ex_summary['num_correct_attempts'], ex_summary['num_correct_first_attempts'], ex_summary['num_correct_second_attempts'], ex_summary['num_correct_third_attempts'], ex_summary['median_num_attempts_to_fca'], ex_summary['median_attempt_time'], most_freq_incorrect_answer_str])
        rw.write(content, indent = 1)
        
    rw.write([""])
