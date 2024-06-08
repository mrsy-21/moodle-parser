import sqlite3
import os
import json
from typing import List
import colors
import shutil

print(f"[{colors.Colors.GREEN}OK{colors.Colors.RESET}] Create Data Base...")

db_name: str = 'scraper_data.db'

connection = sqlite3.connect(db_name)
cur = connection.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS Courses (id_course INTEGER PRIMARY KEY, course_name TEXT)")

with open('courses_name.json', 'r', encoding='utf-8') as file:
    courses_name: List[str] = json.load(file)

for data in courses_name:
    cur.execute("INSERT OR IGNORE INTO Courses (course_name) VALUES (?)", (data,))

connection.commit()

for course_name in courses_name:
    course_name.strip()
    table_name: str = '_'.join(course_name.split()).replace('`', '')
    cur.execute(
        f"CREATE TABLE IF NOT EXISTS \"{table_name}\" (id_file INTEGER PRIMARY KEY, file_name TEXT, file_path TEXT, course_id INTEGER, FOREIGN KEY(course_id) REFERENCES Courses(id_course))")

    course_folder: str = os.path.join('downloads_files_from_courses', course_name.strip())
    if os.path.exists(course_folder):
        for file_name in os.listdir(course_folder):
            file_path: str = os.path.abspath(os.path.join(course_folder, file_name))
            insert_query = f"INSERT INTO \"{table_name}\" (file_name, file_path, course_id) VALUES (?, ?, (SELECT id_course FROM Courses WHERE course_name = ?))"
            cur.execute(insert_query, (file_name, file_path, course_name))

connection.commit()

cur.close()
connection.close()

files_to_delete = ["course_urls.json", "courses_name.json"]
for file in files_to_delete:
    os.remove(file)

shutil.rmtree("source-links-on-course")

print(f"[{colors.Colors.GREEN}OK{colors.Colors.RESET}] Data Base create completed!")
input("Press any key for exit!")
