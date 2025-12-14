from django.contrib import admin
from django.urls import path,include
from userApp import views
from django.shortcuts import redirect

urlpatterns = [
    
   # path('',views.index,name="home"),
    path("", lambda request: redirect("login")),
    path("login/", views.loginUser, name="login"),
    path("logout/", views.logoutUser, name="logout"),
    path("student/dashboard/", views.student_dashboard, name="student_dashboard"),
    path("faculty/dashboard/", views.faculty_dashboard, name="faculty_dashboard"),
    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("attendance/form/", views.attendance_form, name="attendance_form"),
   # path("attendance/get_classes/", views.get_classes, name="get_classes"),
   # path("attendance/get_years/", views.get_years, name="get_years"),
   # path("attendance/get_subjects/", views.get_subjects, name="get_subjects"),
    path("attendance/get_students/", views.get_students, name="get_students"),
    path("attendance/submit/", views.submit_attendance, name="submit_attendance"),
    path("attendance/success/", views.submit_attendance, name="attendance_success"),
    path("attendance/faculty/view/", views.faculty_view_attendance, name="faculty_view_attendance"),
    path("attendance/faculty/details/<str:group_id>/", views.faculty_view_details, name="faculty_view_details"),
    path("dashboard/admin/attendance/", views.admin_view_attendance, name="admin_view_attendance"),
   # path("admin/attendance/details/<str:group_id>/", views.admin_view_details, name="admin_view_details"),
    path("dashboard/admin/details/<str:group_id>/", views.admin_view_details, name="admin_view_details"),
    path("dashboard/admin/details/<str:record_id>/", views.admin_view_details, name="admin_view_details"),
    path("dashboard/admin/class-report/", views.admin_class_report, name="admin_class_report"),
    path("dashboard/admin/defaulters/", views.admin_defaulters, name="admin_defaulters"),
    path("dashboard/student/", views.student_dashboard, name="student_dashboard"),

    path("student/attendance/overall/", views.student_overall_attendance, name="student_overall_attendance"),
    path("student/attendance/subject/", views.student_subject_attendance, name="student_subject_attendance"),
    path("student/attendance/history/", views.student_attendance_history, name="student_attendance_history"),
]


