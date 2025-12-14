from django.shortcuts import render, redirect
from django.contrib import messages
from supabase_client import get_supabase
from .decorators import role_required
from datetime import date
from django.http import JsonResponse, HttpResponseBadRequest
from collections import Counter
import random

def loginUser(request):
    if request.method == "POST":
        email = request.POST.get("username").strip().lower()
        password = request.POST.get("password")

        supabase = get_supabase()
        res = supabase.table("users").select("*").eq("email", email).eq("password", password).execute()

        if res.data:
            user = res.data[0]
            request.session["email"] = user["email"]
            request.session["role"] = user["role"].lower()

            if user["role"].lower()== "admin":
                return redirect("admin_dashboard")
            elif user["role"].lower() == "faculty":
                return redirect("faculty_dashboard")
            else:
                return redirect("student_dashboard")

        messages.error(request, "Invalid Email or Password")
        return redirect("login")

    return render(request, "login.html")
def logoutUser(request):
    request.session.flush()
    return redirect("login")

@role_required("student")
def student_dashboard(request):
    return render(request, "StudentDashboard.html")

@role_required("faculty")
def faculty_dashboard(request):
    return render(request, "FacultyDashboard.html")
@role_required("faculty")
def attendance_form(request):

    faculty_email = request.session.get("email")
    supabase = get_supabase()

    # Fetch classes, subjects, years taught by this faculty
    res = supabase.table("timetable").select("class,subject,year").eq("faculty_email", faculty_email).execute()

    rows = res.data

    classes = sorted(set(r["class"] for r in rows))
    subjects = sorted(set(r["subject"] for r in rows))
    years = sorted(set(r["year"] for r in rows))

    return render(request, "AttendanceForm.html", {
        "classes": classes,
        "subjects": subjects,
        "years": years
    })


def get_students(request):
    selected_class = request.GET.get("class")
    selected_year = request.GET.get("year")

    supabase = get_supabase()

    res = supabase.table("students") \
        .select("name,enrollment_no") \
        .eq("class", selected_class) \
        .eq("year", selected_year) \
        .order("enrollment_no") \
        .execute()

    return JsonResponse({"students": res.data})

def submit_attendance(request):
    if request.method == "POST":
        supabase = get_supabase()

        faculty = request.session.get("email")
        class_name = request.POST.get("class")
        subject = request.POST.get("subject")
        year = request.POST.get("year")
        day = request.POST.get("day")
        timeslot = request.POST.get("time")
        batch = request.POST.get("batch")

        attendance_date = str(date.today())

        attendance_data = []
        present_count = 0
        absent_count = 0

        # ✅ Create group_id (unique for each lecture)
        group_id = f"{class_name}_{subject}_{day}_{timeslot}".replace(" ", "_")


        # Loop through attendance marked
        for key, value in request.POST.items():

            # Enrollment numbers begin with "0827"
            if key.startswith("0827"):

                # Count present/absent
                if value == "Present":
                    present_count += 1
                else:
                    absent_count += 1

                # Insert each student's row
                attendance_data.append({
                    "group_id": group_id,
                    "faculty_email": faculty,
                    "class": class_name,
                    "subject": subject,
                    "year": year,
                    "day": day,
                    "time": timeslot,
                    "attendance_status": value,
                    "attendance_date": attendance_date,
                    "batch": batch,
                    "enrollment_no": key
                })

        # Insert data into supabase
        if attendance_data:
            supabase.table("attendance").insert(attendance_data).execute()

        # Data for success page
        context = {
            "date": attendance_date,
            "faculty": faculty,
            "class": class_name,
            "subject": subject,
            "year": year,
            "day": day,
            "time": timeslot,
            "present_count": present_count,
            "absent_count": absent_count,
            "group_id": group_id,   # Pass group_id (optional)
        }

        return render(request, "attendance_success.html", context)

    return redirect("faculty_dashboard")

def faculty_view_attendance(request):
    supabase = get_supabase()
    faculty = request.session.get("email")

    # Fetch all attendance rows for this faculty
    response = supabase.table("attendance") \
        .select("*") \
        .eq("faculty_email", faculty) \
        .order("attendance_date", desc=True) \
        .execute()

    rows = response.data

    grouped = {}

    for row in rows:
        gid = row.get("group_id")
        if not gid:
            continue   # Ignore old data without group_id

        if gid not in grouped:
            grouped[gid] = {
                "group_id": gid,
                "attendance_date": row["attendance_date"],
                "class": row["class"],
                "subject": row["subject"],
                "year": row["year"],
                "day": row["day"],
                "time": row["time"],
                "present": 0,
                "absent": 0
            }

        if row["attendance_status"] == "Present":
            grouped[gid]["present"] += 1
        else:
            grouped[gid]["absent"] += 1

    summary_list = list(grouped.values())

    return render(request, "faculty_view_attendance.html", {
        "records": summary_list
    })

def faculty_view_details(request, group_id):
    supabase = get_supabase()
    faculty = request.session.get("email")

    # Fetch all attendance rows with this group_id
    response = supabase.table("attendance") \
        .select("*") \
        .eq("faculty_email", faculty) \
        .eq("group_id", group_id) \
        .order("enrollment_no") \
        .execute()

    rows = response.data

    if not rows:
        return render(request, "FacultyDetails.html", {
            "error": "No attendance details found."
        })

    # Lecture info (same for all rows in the group)
    lecture_info = {
        "date": rows[0]["attendance_date"],
        "class": rows[0]["class"],
        "subject": rows[0]["subject"],
        "year": rows[0]["year"],
        "day": rows[0]["day"],
        "time": rows[0]["time"],
        "group_id": group_id
    }

    return render(request, "FacultyDetails.html", {
        "lecture": lecture_info,
        "students": rows
    })


@role_required("admin")
def admin_dashboard(request):
    supabase = get_supabase()

    # Total Students
    total_students = len(
        supabase.table("students").select("enrollment_no").execute().data
    )

    # Total Faculty
    total_faculty = len(
        supabase.table("faculty").select("email").execute().data
    )

    # Total Attendance Records
    total_attendance = len(
        supabase.table("attendance").select("group_id").execute().data
    )

    # Latest Attendance Groups (5)
    response = supabase.table("attendance") \
        .select("group_id, attendance_date, class, subject, year, day, time") \
        .order("attendance_date", desc=True) \
        .limit(20) \
        .execute()

    rows = response.data

    # Deduplicate by group_id
    seen = set()
    latest = []
    for row in rows:
        gid = row["group_id"]
        if gid not in seen:
            seen.add(gid)
            latest.append(row)
        if len(latest) == 5:
            break

    context = {
        "total_students": total_students,
        "total_faculty": total_faculty,
        "total_attendance": total_attendance,
        "latest_groups": latest
    }
    filter_date = request.GET.get("date")
    filter_class = request.GET.get("class")
    filter_faculty = request.GET.get("faculty")
    filter_subject = request.GET.get("subject")
    filter_year = request.GET.get("year")

    query = supabase.table("attendance").select(
        "group_id, faculty_email, class, subject, year, day, time, attendance_date"
    )

    if filter_date:
        query = query.eq("attendance_date", filter_date)

    if filter_class:
        query = query.eq("class", filter_class)

    if filter_faculty:
        query = query.eq("faculty_email", filter_faculty)

    if filter_subject:
        query = query.eq("subject", filter_subject)

    if filter_year:
        query = query.eq("year", filter_year)

    result = query.execute()

    # ---- Remove duplicates using group_id ----
    groups = {}
    for row in result.data:
        groups[row["group_id"]] = row

    # Dynamic dropdowns
    student_classes = supabase.table("students").select("class").execute().data
    classes = sorted(list(set([c["class"] for c in student_classes])))

    faculty_list = supabase.table("users").select("email").eq("role", "Faculty").execute().data

    subject_list = supabase.table("timetable").select("subject").execute().data
    subjects = sorted(list(set([x["subject"] for x in subject_list])))

    years = ["I", "II", "III", "IV"]

    context = {
        "records": list(groups.values()),
        "classes": classes,
        "faculty_list": faculty_list,
        "subjects": subjects,
        "years": years,
    }


    return render(request, "AdminDashboard.html", context)

@role_required("admin")
def admin_view_attendance(request):
    supabase = get_supabase()

    response = supabase.table("attendance").select("*").execute()
    rows = response.data

    grouped = {}

    for row in rows:
        gid = row["group_id"]
        if gid not in grouped:
            grouped[gid] = {
                "group_id": gid,
                "attendance_date": row["attendance_date"],
                "class": row["class"],
                "subject": row["subject"],
                "year": row["year"],
                "day": row["day"],
                "time": row["time"],
                "present": 0,
                "absent": 0
            }

        if row["attendance_status"] == "Present":
            grouped[gid]["present"] += 1
        else:
            grouped[gid]["absent"] += 1

    return render(request, "admin_attendance_list.html", {
        "records": grouped.values()
    })
@role_required("admin")
def admin_view_details(request, group_id):
    supabase = get_supabase()

    response = supabase.table("attendance") \
        .select("*") \
        .eq("group_id", group_id) \
        .order("enrollment_no") \
        .execute()

    rows = response.data

    if not rows:
        return render(request, "admin_attendance_details.html", {
            "error": "No records found."
        })

    lecture = {
        "date": rows[0]["attendance_date"],
        "class": rows[0]["class"],
        "subject": rows[0]["subject"],
        "year": rows[0]["year"],
        "day": rows[0]["day"],
        "time": rows[0]["time"],
    }

    return render(request, "admin_attendance_details.html", {
        "lecture": lecture,
        "students": rows
    })
def admin_class_report(request):
    supabase = get_supabase()

    class_name = request.GET.get("class")
    year = request.GET.get("year")
    subject = request.GET.get("subject")

    if not class_name or not year:
        return render(request, "ClassReport.html", {"students": []})

    # Fetch all students of the class & year
    students = supabase.table("students").select("*") \
                .eq("class", class_name).eq("year", year).execute().data

    # Fetch attendance for the same class-year
    attendance = supabase.table("attendance").select("*") \
                    .eq("class", class_name).eq("year", year).execute().data

    # If subject filter applied
    if subject:
        attendance = [a for a in attendance if a["subject"] == subject]

    report = []

    for student in students:
        enroll = student["enrollment_no"]

        student_att = [a for a in attendance if a["enrollment_no"] == enroll]

        total_lectures = len(student_att)
        present = len([a for a in student_att if a["attendance_status"] == "Present"])
        absent = total_lectures - present

        percentage = round((present / total_lectures) * 100, 2) if total_lectures else 0

        report.append({
            "enrollment": enroll,
            "name": student["name"],
            "total": total_lectures,
            "present": present,
            "absent": absent,
            "percentage": percentage
        })

    # Sort by enrollment
    report = sorted(report, key=lambda x: x["enrollment"])

    context = {
        "students": report,
        "class": class_name,
        "year": year,
        "subject": subject
    }

    return render(request, "ClassReport.html", context)
def admin_defaulters(request):
    supabase = get_supabase()

    class_name = request.GET.get("class")
    year = request.GET.get("year")
    subject = request.GET.get("subject")

    if not class_name or not year:
        return render(request, "Defaulters.html", {"defaulters": []})

    # Students
    students = supabase.table("students").select("*") \
                .eq("class", class_name).eq("year", year).execute().data

    # Attendance
    attendance = supabase.table("attendance").select("*") \
                    .eq("class", class_name).eq("year", year).execute().data

    if subject:
        attendance = [a for a in attendance if a["subject"] == subject]

    defaulters = []

    for student in students:
        enroll = student["enrollment_no"]
        student_att = [a for a in attendance if a["enrollment_no"] == enroll]

        total = len(student_att)
        present = len([a for a in student_att if a["attendance_status"] == "Present"])
        percent = round((present / total) * 100, 2) if total else 0

        if percent < 75:
            defaulters.append({
                "enrollment": enroll,
                "name": student["name"],
                "percentage": percent
            })

    # Sort ascending by %
    defaulters = sorted(defaulters, key=lambda x: x["percentage"])

    return render(request, "Defaulters.html", {"defaulters": defaulters})

@role_required("student")
def student_dashboard(request):
    student_email = request.session.get("email")
    if not student_email:
        return redirect("login")

    supabase = get_supabase()

    # Fetch student details
    data = supabase.table("students").select("*").eq("email", student_email).execute().data

    if not data:
        return render(request, "StudentDashboard.html", {"error": "Student record not found!"})

    student = data[0]

    return render(request, "StudentDashboard.html", {"student": student})
def student_overall_attendance(request):
    supabase = get_supabase()
    email = request.session.get("email")

    student = supabase.table("students").select("*").eq("email", email).execute().data[0]
    enroll = student["enrollment_no"]

    attendance = supabase.table("attendance").select("*").eq("enrollment_no", enroll).execute().data

    total = len(attendance)
    present = len([a for a in attendance if a["attendance_status"] == "Present"])
    absent = total - present
    percent = round((present / total) * 100, 2) if total else 0

    context = {
        "name": student["name"],
        "enrollment": enroll,
        "total": total,
        "present": present,
        "absent": absent,
        "percent": percent,
    }

    return render(request, "StudentOverall.html", context)
def student_subject_attendance(request):
    supabase = get_supabase()
    email = request.session.get("email")

    student = supabase.table("students").select("*").eq("email", email).execute().data[0]
    enroll = student["enrollment_no"]

    attendance = supabase.table("attendance").select("*").eq("enrollment_no", enroll).execute().data

    subjects = {}

    for a in attendance:
        sub = a["subject"]
        if sub not in subjects:
            subjects[sub] = {"total": 0, "present": 0}
        subjects[sub]["total"] += 1
        if a["attendance_status"] == "Present":
            subjects[sub]["present"] += 1

    # Create final report
    report = []
    for sub, data in subjects.items():
        percent = round((data["present"] / data["total"]) * 100, 2)
        report.append({
            "subject": sub,
            "total": data["total"],
            "present": data["present"],
            "absent": data["total"] - data["present"],
            "percent": percent
        })

    return render(request, "StudentSubject.html", {"report": report})
def student_attendance_history(request):
    supabase = get_supabase()
    email = request.session.get("email")

    student = supabase.table("students").select("*").eq("email", email).execute().data[0]
    enroll = student["enrollment_no"]

    attendance = supabase.table("attendance").select("*") \
                        .eq("enrollment_no", enroll).order("attendance_date").execute().data

    return render(request, "StudentHistory.html", {"attendance": attendance})
