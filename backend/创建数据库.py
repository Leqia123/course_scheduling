import psycopg2
#建立数据库连接
con = psycopg2.connect(database="postgres", user="postgres", password="031104", host="localhost", port="5432")
#调用游标对象
cur = con.cursor()
#用cursor中的execute 使用DDL语句创建一个名为 STUDENT 的表,指定表的字段以及字段类型
select_query = """-- 假设 user 'leqijia' 的 id 是 1009 (根据你的 users 插入语句)
-- SQL for PostgreSQL
-- 1. Create Tables

CREATE TABLE semesters (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL
);

CREATE TABLE majors (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    total_sessions INT NOT NULL CHECK (total_sessions >= 0),
    course_type VARCHAR(50) DEFAULT '理论课'
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL, -- WARNING: Plain text password! Use hashing in production.
    role VARCHAR(50) NOT NULL
);

CREATE TABLE teachers (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE -- Link to the user account
);

-- Junction table for M:N relationship between teachers and the courses they can teach
CREATE TABLE teacher_course_permissions (
    teacher_id INT NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    course_id INT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    PRIMARY KEY (teacher_id, course_id) -- Ensure unique pairings
);

CREATE TABLE classrooms (
    id INT PRIMARY KEY,
    building VARCHAR(100) NOT NULL,
    room_number VARCHAR(50) NOT NULL,
    capacity INT DEFAULT 0 CHECK (capacity >= 0),
    room_type VARCHAR(50) DEFAULT '普通教室',
    UNIQUE (building, room_number) -- Optional: Ensure building/room combo is unique
);

CREATE TABLE time_slots (
    id INT PRIMARY KEY,
    day_of_week VARCHAR(10) NOT NULL, -- e.g., '周一', '周二'
    period INT NOT NULL, -- e.g., 1, 2, 3, 4
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    UNIQUE (day_of_week, period) -- Ensure unique day/period combo
);

-- Use SERIAL for automatic ID generation if preferred, otherwise manage IDs manually
-- CREATE SEQUENCE course_assignments_id_seq; -- Or use SERIAL directly
CREATE TABLE course_assignments (
    id SERIAL PRIMARY KEY, -- Or: id SERIAL PRIMARY KEY
    major_id INT NOT NULL REFERENCES majors(id),
    course_id INT NOT NULL REFERENCES courses(id),
    teacher_id INT NOT NULL REFERENCES teachers(id),
    semester_id INT NOT NULL REFERENCES semesters(id),
    is_core_course BOOLEAN DEFAULT FALSE,
    expected_students INT DEFAULT 0 CHECK (expected_students >= 0)
    -- Optional: UNIQUE constraint if a specific combo shouldn't be duplicated
    -- UNIQUE (major_id, course_id, teacher_id, semester_id)
);

-- Table to store the final schedule results (optional, if you want to save results to DB)
CREATE TABLE timetable_entries (
    id SERIAL PRIMARY KEY, -- Auto-incrementing ID
    semester_id INT NOT NULL REFERENCES semesters(id),
    major_id INT NOT NULL REFERENCES majors(id),
    course_id INT NOT NULL REFERENCES courses(id),
    teacher_id INT NOT NULL REFERENCES teachers(id),
    classroom_id INT NOT NULL REFERENCES classrooms(id),
    timeslot_id INT NOT NULL REFERENCES time_slots(id),
    week_number INT NOT NULL CHECK (week_number > 0),
    assignment_id INT NOT NULL REFERENCES course_assignments(id) ON DELETE CASCADE -- Link back to the assignment
);
create TABLE students
(
	id SERIAL PRIMARY KEY,
	user_id INT NOT NULL	REFERENCES users(id) ON DELETE CASCADE,
	major_id INT NOT NULL REFERENCES majors(id),
	student_id_number VARCHAR(100) UNIQUE
);
create TABLE teacher_scheduling_preferences
(
	id SERIAL PRIMARY KEY,
	teacher_id INT NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
	semester_id INT NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
	timeslot_id INT NOT NULL REFERENCES time_slots(id) ON DELETE CASCADE,
	preference_type VARCHAR(50) NOT NULL,
	reason TEXT,
	status VARCHAR(50) DEFAULT 'pending'::character varying,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
	constraint teacher_scheduling_preference_teacher_id_semester_id_timesl_key
		unique (teacher_id, semester_id, timeslot_id, preference_type)
);

-- 2. Insert Data

-- Insert Semesters
INSERT INTO semesters (id, name, start_date, end_date) VALUES
(1, '2023-2024学年秋季', '2023-09-04', '2024-01-19');



-- Insert Majors
INSERT INTO majors (id, name) VALUES
(1, '计算机科学与技术'),
(2, '电子信息工程'),
(3, '软件工程'),
(4, '机械工程'),
(5, '生物工程');

-- Insert Courses
INSERT INTO courses (id, name, total_sessions, course_type) VALUES
(101, '高等数学A', 24, '理论课'),
(102, '线性代数', 16, '理论课'),
(103, '大学英语1', 28, '理论课'),
(104, '大学物理', 20, '理论课'),
(105, '体育基础', 12, '理论课'),
(401, 'C++程序设计', 24, '理论课'),
(402, '数据结构', 20, '理论课'),
(403, '操作系统', 18, '理论课'),
(404, '计算机组成原理', 20, '理论课'),
(405, '算法分析与设计', 16, '理论课'),
(406, '数据库原理', 18, '理论课'),
(407, '软件工程实践', 16, '实验课'),
(408, '离散数学', 16, '理论课'),
(201, '模拟电路', 20, '理论课'),
(202, '信号与系统', 16, '理论课'),
(203, '雷达原理', 16, '理论课'),
(204, '数字电路', 18, '理论课'),
(205, '电路分析', 24, '理论课'),
(206, '单片机原理与应用', 16, '实验课'),
(207, '通信原理', 18, '理论课'),
(501, '工程力学A', 20, '理论课'),
(502, '机械原理', 20, '理论课'),
(503, '材料力学', 18, '理论课'),
(504, '机械设计基础', 24, '理论课'),
(505, '工程制图', 16, '理论课'),
(506, '数控机床操作', 16, '实验课'),
(601, '生物化学', 18, '理论课'),
(602, '微生物学', 16, '理论课'),
(603, '生物工程导论', 16, '理论课'),
(604, '基因工程', 20, '理论课'),
(605, '生物实验技术', 16, '实验课');

-- Insert Users
INSERT INTO users (id, username, password, role) VALUES
(1001, '李老师', '123', 'teacher'), -- INSECURE! HASH PASSWORDS!
(1002, '王老师', '123', 'teacher'),
(1003, '张老师', '123', 'teacher'),
(1004, '赵老师', '123', 'teacher'),
(1005, '钱老师', '123', 'teacher'),
(1006, '孙老师', '123', 'teacher'),
(1007, '周老师', '123', 'teacher'),
(1008, '吴老师', '123', 'teacher'),
(1009, 'leqijia', '123', 'student'),
(1010, 'admin', '123', 'admin');

-- Insert Students
INSERT INTO students (id,user_id,major_id,student_id_number) VALUES
(1,1009,1,'S20230001');

-- Insert Teachers (linking to users)
INSERT INTO teachers (id, user_id) VALUES
(1, 1001),
(2, 1002),
(3, 1003),
(4, 1004),
(5, 1005),
(6, 1006),
(7, 1007),
(8, 1008);

-- Insert Teacher Course Permissions
-- Teacher 1 (李老师)
INSERT INTO teacher_course_permissions (teacher_id, course_id) VALUES (1, 101), (1, 102), (1, 408), (1, 405);
-- Teacher 2 (王老师)
INSERT INTO teacher_course_permissions (teacher_id, course_id) VALUES (2, 103), (2, 105), (2, 601);
-- Teacher 3 (张老师)
INSERT INTO teacher_course_permissions (teacher_id, course_id) VALUES (3, 401), (3, 402), (3, 403), (3, 406);
-- Teacher 4 (赵老师)
INSERT INTO teacher_course_permissions (teacher_id, course_id) VALUES (4, 201), (4, 204), (4, 205), (4, 207);
-- Teacher 5 (钱老师)
INSERT INTO teacher_course_permissions (teacher_id, course_id) VALUES (5, 501), (5, 502), (5, 503), (5, 504), (5, 505);
-- Teacher 6 (孙老师)
INSERT INTO teacher_course_permissions (teacher_id, course_id) VALUES (6, 104), (6, 202), (6, 203), (6, 602);
-- Teacher 7 (周老师)
INSERT INTO teacher_course_permissions (teacher_id, course_id) VALUES (7, 404), (7, 603), (7, 604);
-- Teacher 8 (吴老师 - 实验课)
INSERT INTO teacher_course_permissions (teacher_id, course_id) VALUES (8, 407), (8, 206), (8, 506), (8, 605);

-- Insert Classrooms
INSERT INTO classrooms (id, building, room_number, capacity, room_type) VALUES
(1, '主楼', '101', 80, '普通教室'),
(2, '主楼', '102', 75, '普通教室'),
(3, '主楼', '103', 90, '普通教室'),
(4, '主楼', '104', 70, '普通教室'),
(5, '主楼', '201', 85, '普通教室'),
(6, '主楼', '301', 60, '普通教室'),
(7, '主楼', '302', 60, '普通教室'),
(8, '实验楼', '201', 50, '实验室'),
(9, '实验楼', '202', 45, '实验室'),
(10, '实验楼', '301', 40, '实验室'),
(11, '实验楼', '401', 90, '实验室');

-- Insert Time Slots
INSERT INTO time_slots (id, day_of_week, period, start_time, end_time) VALUES
(1, '周一', 1, '08:00:00', '09:30:00'), (2, '周一', 2, '09:40:00', '11:10:00'),
(3, '周一', 3, '13:30:00', '15:00:00'), (4, '周一', 4, '15:10:00', '16:40:00'),
(5, '周二', 1, '08:00:00', '09:30:00'), (6, '周二', 2, '09:40:00', '11:10:00'),
(7, '周二', 3, '13:30:00', '15:00:00'), (8, '周二', 4, '15:10:00', '16:40:00'),
(9, '周三', 1, '08:00:00', '09:30:00'), (10, '周三', 2, '09:40:00', '11:10:00'),
(11, '周三', 3, '13:30:00', '15:00:00'), (12, '周三', 4, '15:10:00', '16:40:00'),
(13, '周四', 1, '08:00:00', '09:30:00'), (14, '周四', 2, '09:40:00', '11:10:00'),
(15, '周四', 3, '13:30:00', '15:00:00'), (16, '周四', 4, '15:10:00', '16:40:00'),
(17, '周五', 1, '08:00:00', '09:30:00'), (18, '周五', 2, '09:40:00', '11:10:00'),
(19, '周五', 3, '13:30:00', '15:00:00'), (20, '周五', 4, '15:10:00', '16:40:00'),
(21, '周六', 1, '08:00:00', '09:30:00'), (22, '周六', 2, '09:40:00', '11:10:00'),
(23, '周六', 3, '13:30:00', '15:00:00'), (24, '周六', 4, '15:10:00', '16:40:00'),
(25, '周日', 1, '08:00:00', '09:30:00'), (26, '周日', 2, '09:40:00', '11:10:00'),
(27, '周日', 3, '13:30:00', '15:00:00'), (28, '周日', 4, '15:10:00', '16:40:00');

-- Insert Course Assignments (Manually assign IDs starting from 1)
-- Make sure semester_id=1 matches the semester inserted above
INSERT INTO course_assignments (id, major_id, course_id, teacher_id, semester_id, is_core_course, expected_students) VALUES
(1, 1, 101, 1, 1, TRUE, 75), (2, 1, 102, 1, 1, TRUE, 75), (3, 1, 103, 2, 1, TRUE, 75),
(4, 1, 401, 3, 1, TRUE, 75), (5, 1, 402, 3, 1, TRUE, 75), (6, 1, 403, 3, 1, TRUE, 75),
(7, 1, 404, 7, 1, TRUE, 75), (8, 1, 405, 1, 1, TRUE, 75), (9, 1, 406, 3, 1, FALSE, 75),
(10, 1, 408, 1, 1, FALSE, 75), (11, 1, 407, 8, 1, TRUE, 75),
(12, 2, 101, 1, 1, TRUE, 65), (13, 2, 102, 1, 1, TRUE, 65), (14, 2, 103, 2, 1, TRUE, 65),
(15, 2, 104, 6, 1, TRUE, 65), (16, 2, 201, 4, 1, TRUE, 65), (17, 2, 202, 6, 1, TRUE, 65),
(18, 2, 203, 6, 1, FALSE, 65), (19, 2, 204, 4, 1, TRUE, 65), (20, 2, 205, 4, 1, TRUE, 65),
(21, 2, 207, 4, 1, FALSE, 65), (22, 2, 206, 8, 1, TRUE, 65),
(23, 3, 101, 1, 1, TRUE, 80), (24, 3, 103, 2, 1, TRUE, 80), (25, 3, 401, 3, 1, TRUE, 80),
(26, 3, 402, 3, 1, TRUE, 80), (27, 3, 403, 3, 1, TRUE, 80), (28, 3, 406, 3, 1, TRUE, 80),
(29, 3, 404, 7, 1, FALSE, 80), (30, 3, 405, 1, 1, FALSE, 80), (31, 3, 407, 8, 1, TRUE, 80),
(32, 4, 101, 1, 1, TRUE, 60), (33, 4, 103, 2, 1, TRUE, 60), (34, 4, 104, 6, 1, TRUE, 60),
(35, 4, 501, 5, 1, TRUE, 60), (36, 4, 502, 5, 1, TRUE, 60), (37, 4, 503, 5, 1, TRUE, 60),
(38, 4, 504, 5, 1, TRUE, 60), (39, 4, 505, 5, 1, FALSE, 60), (40, 4, 506, 8, 1, TRUE, 60),
(41, 5, 103, 2, 1, TRUE, 55), (42, 5, 104, 6, 1, TRUE, 55), (43, 5, 601, 2, 1, TRUE, 55),
(44, 5, 602, 6, 1, TRUE, 55), (45, 5, 603, 7, 1, TRUE, 55), (46, 5, 604, 7, 1, FALSE, 55),
(47, 5, 605, 8, 1, TRUE, 55);

-- Add indexes for performance on foreign keys and frequently queried columns
CREATE INDEX idx_course_assignments_major ON course_assignments (major_id);
CREATE INDEX idx_course_assignments_course ON course_assignments (course_id);
CREATE INDEX idx_course_assignments_teacher ON course_assignments (teacher_id);
CREATE INDEX idx_course_assignments_semester ON course_assignments (semester_id);
CREATE INDEX idx_timetable_entries_week ON timetable_entries (week_number);
CREATE INDEX idx_timetable_entries_timeslot ON timetable_entries (timeslot_id);
CREATE INDEX idx_timetable_entries_classroom ON timetable_entries (classroom_id);
CREATE INDEX idx_teacher_course_permissions_course ON teacher_course_permissions (course_id);

"""
cur.execute(select_query)
# records = cur.fetchall()
#
# print("Printing each row")
# for row in records:
#     print("ID =", row[0], )
#     print("Name =", row[1])
#     print("Age =", row[2])
#     print("Position =", row[3], "\n")


#提交更改，增添或者修改数据只会必须要提交才能生效
con.commit()
con.close()
