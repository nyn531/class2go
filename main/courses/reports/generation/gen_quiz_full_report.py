from c2g.models import *
from datetime import datetime
import json
from courses.reports.generation.C2GReportWriter import *
from courses.reports.generation.get_quiz_data import *

def gen_quiz_full_report(ready_course, ready_quiz, save_to_s3=False):

    ### 1- Create the S3 file name and report writer object
    dt = datetime.now()
    course_prefix = ready_course.handle.split('--')[0]
    course_suffix = ready_course.handle.split('--')[1]
    is_video = isinstance(ready_quiz, Video)
    is_summative = (not is_video) and (ready_quiz.assessment_type == 'assessive')
    
    report_name = "%02d_%02d_%02d__%02d_%02d_%02d-%s.csv" % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, ready_quiz.slug)
    if is_video:
        s3_filepath = "%s/%s/reports/videos/%s" % (course_prefix, course_suffix, report_name)
    else:
        s3_filepath = "%s/%s/reports/problemsets/%s" % (course_prefix, course_suffix, report_name)
    
    rw = C2GReportWriter(save_to_s3, s3_filepath)
    
    ### 2- Get the quiz data
    quiz_data = get_quiz_data(ready_quiz)
    per_student_data = quiz_data['per_student_data']
    exercise_summaries = quiz_data['exercise_summaries']
    
    ### 3- Writeout
    rw.write(["Activity for %s" % quiz_data['quiz_summary']['title']], nl = 1) 

    # Sort students by username
    sorted_usernames = sorted(per_student_data.keys())
    
    # If no activity, do not type anything unneeded.
    if not has_activity(per_student_data):
        rw.write(content=["No activity yet."], indent=1)
        report_content = rw.writeout()
        return {'name': report_name, 'path': s3_filepath, 'content': report_content}
        
    header1 = ["", ""]
    header2 = ["", ""]
    
    header1.extend(["", "", "Num page visits", "Visit date/times"])
    header2.extend(["", "", "", ""])
        
    for ex_id in exercise_summaries:
        ex_summary = exercise_summaries[ex_id]
        
        header1.extend(["", "", ex_summary['slug'], "", "", ""])
        header2.extend(["", "", "Completed", "Attempts", "Score", "Median attempt time"])
        if is_summative:
            header1.extend(["",""])
            header2.extend(["First correct attempt timestamp", "Score after late penalty"])
        
    header1.extend(["", "Total score / %d"  % len(exercise_summaries)])
    if is_summative: header1.extend(["Total score after late penalty"])
    
    rw.write(header1)
    rw.write(header2)
    
    for u in sorted_usernames:
        stud_quiz_data = per_student_data[u]
        
        if len(stud_quiz_data['visits']) == 0 and len(stud_quiz_data['exercise_activity']) == 0:
            continue
        
        stud_score = 0
        stud_score_after_late_penalty = 0
        
        # User- and full name
        content = [u, stud_quiz_data['name']]
        
        # Student visit data
        content.extend([ "", "", len(stud_quiz_data['visits']), ", ".join(stud_quiz_data['visits']) ])
        
        for ex_id in exercise_summaries:
            if ex_id in stud_quiz_data['exercise_activity']: ex_res = stud_quiz_data['exercise_activity'][ex_id]
            else: ex_res = {'completed': '', 'attempts': '', 'score': '', 'last_attempt_timestamp': '', 'score_after_late_penalty': '', 'median_attempt_time': ''}
            
            content.extend(["", "", 'y' if ex_res['completed'] else 'n', ex_res['attempts'], ex_res['score'], ex_res['median_attempt_time']])
            if is_summative:
                first_correct_attempt_timestamp = get_friendly_datetime(ex_res['last_attempt_timestamp']) if ex_res['completed'] else ""
                content.extend([first_correct_attempt_timestamp, ex_res['score_after_late_penalty']])
            
            stud_score += (ex_res['score'] if isinstance(ex_res['score'], float) else 0)
            if is_summative and isinstance(ex_res['score_after_late_penalty'], float):
                stud_score_after_late_penalty += ex_res['score_after_late_penalty']

        content.extend(["", stud_score])
        if is_summative:
            content.append(stud_score_after_late_penalty)
            
        rw.write(content)
        
    report_content = rw.writeout()
    return {'name': report_name, 'content': report_content, 'path': s3_filepath}

def get_friendly_datetime(dt):
    if isinstance(dt, datetime):
        return "{0}-{1}-{2} at {3}:{4}".format(dt.month, dt.day, dt.year, dt.hour, dt.minute)
    else:
        return ""
        
def has_activity(per_student_data):
    for u in per_student_data.keys():
        if len(per_student_data[u]['visits']) > 0 or len(per_student_data[u]['exercise_activity']) > 0:
            return True
            
    return False