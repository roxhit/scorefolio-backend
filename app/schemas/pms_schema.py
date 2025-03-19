def returnStudent(student) -> dict:
    return {
        "name": student.get("name"),
        "contact": student.get("contact"),
        "email": student.get("email"),
        "basic_details": student.get("basic_details", {}),
        "tenth_details": student.get("tenth_details", {}),
        "twelfth_details": student.get("twelfth_details", {}),
        "semester_details": student.get("semester_details", []),
    }


def list_serial_student(students) -> list:
    return [returnStudent(student) for student in students]
