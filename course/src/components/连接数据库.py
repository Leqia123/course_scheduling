import psycopg2
#建立数据库连接
con = psycopg2.connect(database="postgres", user="postgres", password="031104", host="localhost", port="5432")
#调用游标对象
cur = con.cursor()
#用cursor中的execute 使用DDL语句创建一个名为 STUDENT 的表,指定表的字段以及字段类型
select_query = """-- 假设 user 'leqijia' 的 id 是 1009 (根据你的 users 插入语句)
-- SQL for PostgreSQL

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

;
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
