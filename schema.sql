-- Database schema for timetable_ai
DROP TABLE IF EXISTS timetable;
CREATE TABLE timetable (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    day TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL
);
