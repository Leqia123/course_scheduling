import os
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values, DictCursor  # Added DictCursor if needed
import pandas as pd
import io
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import datetime
import re
# werkzeug.utils is already imported implicitly by Flask, but good to be explicit if using functions
# from werkzeug.utils import secure_filename # Uncomment if you explicitly use secure_filename

# Assume scheduler_module.py is available and imported correctly
# Make sure your scheduler_module.py contains load_data_from_db and generate_excel_report_for_send_file
# and the TimetableEntry class (likely a namedtuple or dataclass)
import scheduler_module

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# --- Database Configuration ---
# TODO: In production, use environment variables exclusively and avoid default sensitive values
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")  # Replace with your DB user
DB_PASSWORD = os.getenv("DB_PASSWORD", "031104")  # Replace with your DB password


# WARNING: Storing password directly in code or env vars is not ideal for production.
# Consider using a secrets management system.
def get_teacher_id_by_user_id(user_id):
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return None
        cur = conn.cursor()
        cur.execute("SELECT id FROM teachers WHERE user_id = %s", (user_id,))
        teacher_id = cur.fetchone()
        cur.close()
        return teacher_id[0] if teacher_id else None
    except Exception as e:
        app.logger.error(f"Error getting teacher_id for user {user_id}: {e}", exc_info=True)
        return None
    finally:
        if cur: cur.close()
        if conn: conn.close()
def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        # conn.autocommit = True # Only enable autocommit if you are sure you don't need transactions
        return conn
    except psycopg2.Error as e:
        # Use app.logger for consistent logging
        app.logger.error(f"Error connecting to PostgreSQL database: {e}")
        return None


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user_type = data.get('userType')

    if not username or not password or not user_type:
        return jsonify({'message': 'All fields are required!'}), 400

    if user_type not in ['student', 'teacher', 'admin']:
        return jsonify({'message': 'Invalid user type.'}), 400

    # 你的 users 表主键是 id (INT)，不是 UserID
    # 并且字段名是 password, role (小写)
    # 密码哈希是好的，但你的数据库 users 表是 password VARCHAR(255) NOT NULL, -- WARNING: Plain text password!
    # 为了匹配你的数据库，我暂时移除了哈希，但强烈建议你在生产环境中使用哈希并修改表结构
    # hashed_password = generate_password_hash(password)
    plain_password = password  # 警告：明文密码

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # 检查你的 users 表的 id 是否是自增的，如果不是，你需要提供 id
        # 假设 users.id 是自增的 (SERIAL) 或者你会在应用层面管理它
        # 如果 users.id 不是自增，你需要从请求中获取或生成它
        # 为了简单，假设它自增，但你的 schema 是 INT PRIMARY KEY
        # 最好改成 SERIAL 或者在插入时提供一个唯一的 id

        # 查找最大的 user_id，然后加1
        cur.execute("SELECT MAX(id) FROM users")
        max_id_result = cur.fetchone()
        next_id = (max_id_result[0] if max_id_result[0] is not None else 0) + 1

        cur.execute(
            "INSERT INTO users (id, username, password, role) VALUES (%s, %s, %s, %s) RETURNING id",  # 注意字段名大小写
            (next_id, username, plain_password, user_type)
        )
        user_id_returned = cur.fetchone()[0]
        conn.commit()
        return jsonify({'message': 'User registered successfully!', 'user_id': user_id_returned}), 201
    except psycopg2.IntegrityError:
        if conn: conn.rollback()
        return jsonify({'message': 'Username already exists or ID conflict!'}), 409
    except Exception as e:
        if conn: conn.rollback()
        print(f"Error during registration: {e}")
        return jsonify({'message': 'An error occurred during registration.'}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    user_type = data.get('userType')  # 前端发送的是 userType

    if not username or not password or not user_type:
        return jsonify({'message': 'All fields are required!'}), 400

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # 确保这里的 users 表列名与数据库一致 (username, password, role)
        cur.execute(
            "SELECT id, password, role FROM users WHERE username = %s",
            (username,)
        )
        user_record = cur.fetchone()

        # 再次强调，你的数据库存的是明文密码，所以直接比较
        # if user_record and check_password_hash(user_record[1], password) and user_record[2] == user_type:
        if user_record and user_record[1] == password and user_record[2] == user_type:
            return jsonify({
                'message': 'Login successful!',
                'user_id': user_record[0],
                'user_role': user_record[2],
                'username': username,  # 将用户名返回给前端
                'token': f'fake-jwt-token-for-{username}'  # 模拟token
            }), 200
        else:
            return jsonify({'message': 'Invalid username, password, or user type.'}), 401
    except Exception as e:
        print(f"Error during login: {e}")
        return jsonify({'message': 'An error occurred during login.'}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


# --- Helper Function ---
def get_id_from_name(cur, table_name, name_column, name_value, id_column='id', additional_conditions=None):
    """Generic function to get ID from a table by name, with optional additional conditions."""
    query = f"SELECT {id_column} FROM {table_name} WHERE {name_column} = %s"
    params = [name_value]
    if additional_conditions:
        for col, val in additional_conditions.items():
            query += f" AND {col} = %s"
            params.append(val)
    # Use SELECT DISTINCT to avoid potential duplicates if your schema allows (it shouldn't for unique names)
    # But given your unique constraints, this is fine.
    cur.execute(query, tuple(params))
    result = cur.fetchone()
    # Fetchone returns None if no row, otherwise a tuple. Need to handle the None case.
    return result[0] if result else None


# 在 app.py 文件顶部导入必要的库
import datetime
import math # 用于向上取整

# ... (其他 import 和 Flask app 设置) ...

@app.route('/api/semesters', methods=['GET'])
def get_semesters():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"message": "数据库连接失败"}), 500
        # 修改 SQL 查询，获取 start_date 和 end_date
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, name, start_date, end_date FROM semesters ORDER BY name DESC;")
        semesters_data = cur.fetchall()

        # 遍历结果，计算 total_weeks 并添加到每个 semester 字典中
        processed_semesters = []
        for semester in semesters_data:
            start_date = semester.get('start_date')
            end_date = semester.get('end_date')
            total_weeks = 0 # 默认值

            # 确保 start_date 和 end_date 是有效的日期对象
            if isinstance(start_date, datetime.date) and isinstance(end_date, datetime.date) and end_date >= start_date:
                # 计算天数差
                delta = end_date - start_date
                # 计算周数：(总天数 + 1) / 7，然后向上取整
                # +1 是因为 delta.days 计算的是间隔天数，我们需要包含起始和结束两天
                # 例如，从周一到周日，delta.days 是 6，但实际上是 7 天，即 1 周。 (6 + 1) / 7 = 1
                # 从周一到下一个周一，delta.days 是 7，实际上是 8 天。 (7 + 1) / 7 = 1.14... -> ceil = 2 周
                duration_days = delta.days + 1
                total_weeks = math.ceil(duration_days / 7)
            else:
                # 如果日期无效或不合逻辑，记录日志（可选）
                app.logger.warning(f"Semester ID {semester.get('id')} has invalid start/end dates: {start_date}, {end_date}. Setting total_weeks to 0.")

            # 将计算得到的 total_weeks 添加到字典中
            semester['total_weeks'] = total_weeks

            # 从返回给前端的数据中移除原始日期，如果前端不需要的话
            # 如果前端需要，可以保留
            # del semester['start_date']
            # del semester['end_date']

            processed_semesters.append(semester)

        # 返回处理后的列表
        return jsonify(processed_semesters)

    except psycopg2.Error as e:
        app.logger.error(f"Database error in get_semesters: {e}")
        return jsonify({"message": "获取学期信息失败"}), 500
    except Exception as e:
        app.logger.error(f"An unexpected error occurred in get_semesters: {e}", exc_info=True)
        return jsonify({"message": "服务器内部错误"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route('/api/course-plans', methods=['GET'])
def get_course_plans():
    semester_id = request.args.get('semester_id', type=int)
    if semester_id is None:  # Check explicitly for None after type conversion
        return jsonify({"message": "semester_id 参数是必需的"}), 400

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # Join with related tables to get names
        query = """
        SELECT
            ca.id,
            ca.semester_id,
            ca.major_id,
            m.name AS major_name,
            ca.course_id,
            c.name AS course_name,
            c.course_type,
            c.total_sessions,
            ca.teacher_id,
            u.username AS teacher_name, -- Assuming teacher's name is in users table
            ca.is_core_course,
            ca.expected_students
        FROM course_assignments ca
        JOIN majors m ON ca.major_id = m.id
        JOIN courses c ON ca.course_id = c.id
        JOIN teachers t ON ca.teacher_id = t.id
        JOIN users u ON t.user_id = u.id -- Link teachers to users to get username
        WHERE ca.semester_id = %s
        ORDER BY m.name, c.name;
        """
        cur.execute(query, (semester_id,))
        plans = cur.fetchall()
        return jsonify(plans)
    except psycopg2.Error as e:
        app.logger.error(f"Database error in get_course_plans for semester {semester_id}: {e}")
        return jsonify({"message": "获取课程计划失败"}), 500
    except Exception as e:
        app.logger.error(f"An unexpected error occurred in get_course_plans: {e}", exc_info=True)
        return jsonify({"message": "服务器内部错误"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route('/api/course-plans/upload', methods=['POST'])
def upload_course_plans():
    if 'file' not in request.files:
        return jsonify({"message": "请求中不包含文件"}), 400

    file = request.files['file']
    # Use getlist(key)[0] for single value, handling potential empty list if key is missing entirely
    semester_id_str = request.form.get('semester_id')  # Get as string first
    semester_id_from_form = None
    if semester_id_str:
        try:
            semester_id_from_form = int(semester_id_str)
        except (ValueError, TypeError):
            return jsonify({"message": "semester_id 参数格式不正确"}), 400

    if file.filename == '':
        return jsonify({"message": "未选择文件"}), 400
    if semester_id_from_form is None:  # Check explicitly for None
        return jsonify({"message": "缺少 semester_id 参数"}), 400
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        return jsonify({"message": "不支持的文件类型。请上传 .xls 或 .xlsx 文件"}), 400

    conn = None
    cur = None
    processed_rows = 0
    created_courses_count = 0
    updated_courses_count = 0
    inserted_assignments_count = 0
    error_messages = []

    try:
        # Use BytesIO to pass the file content to pandas
        file_content = io.BytesIO(file.read())
        df = pd.read_excel(file_content,
                           engine='openpyxl' if file.filename.endswith('.xlsx') else 'xlrd')  # xlrd for .xls
        actual_columns = [str(col).strip() for col in df.columns]  # Ensure columns are strings and strip whitespace
        df.columns = actual_columns

        expected_excel_columns = [
            '学期名称', '专业名称', '课程名称', '总课时',
            '课程类型', '授课教师姓名', '是否核心课程', '预计学生人数'
        ]
        missing_cols = [col for col in expected_excel_columns if col not in df.columns]
        if missing_cols:
            return jsonify({"message": f"Excel 文件缺少必需的列: {', '.join(missing_cols)}"}), 400

        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor()
        conn.autocommit = False  # Start transaction

        # Verify semester ID and get name from DB
        cur.execute("SELECT name FROM semesters WHERE id = %s", (semester_id_from_form,))
        semester_name_from_db_tuple = cur.fetchone()
        if not semester_name_from_db_tuple:
            conn.rollback()
            return jsonify({"message": f"选定的学期ID {semester_id_from_form} 无效"}), 400
        semester_name_from_db = semester_name_from_db_tuple[0]

        # Clear existing assignments for this semester
        cur.execute("DELETE FROM course_assignments WHERE semester_id = %s", (semester_id_from_form,))
        deleted_count = cur.rowcount
        app.logger.info(f"Deleted {deleted_count} old course_assignments for semester_id {semester_id_from_form}.")

        course_assignments_to_insert = []

        # Pre-fetch common IDs to reduce DB queries in loop (Optional optimization)
        # majors_map = {row['name']: row['id'] for row in get_db_connection().cursor(cursor_factory=RealDictCursor).execute("SELECT id, name FROM majors").fetchall()} # Example
        # teachers_map = {row['name']: row['id'] for row in get_db_connection().cursor(cursor_factory=RealDictCursor).execute("SELECT t.id, u.username as name FROM teachers t JOIN users u ON t.user_id = u.id WHERE u.role = 'Teacher'").fetchall()} # Example

        for index, row in df.iterrows():
            processed_rows += 1
            try:
                # Ensure all necessary fields exist and handle potential NaNs from pandas
                excel_semester_name = str(row.get('学期名称', '')).strip()
                major_name = str(row.get('专业名称', '')).strip()
                course_name = str(row.get('课程名称', '')).strip()
                total_sessions_raw = row.get('总课时')
                course_type = str(row.get('课程类型', '')).strip()
                teacher_name = str(row.get('授课教师姓名', '')).strip()
                is_core_course_str = str(row.get('是否核心课程', '')).strip().lower()
                expected_students_raw = row.get('预计学生人数')

                # Basic validation
                if not all([excel_semester_name, major_name, course_name, teacher_name]):
                    error_messages.append(
                        f"Row {index + 2}: 必填字段 (学期名称, 专业名称, 课程名称, 授课教师姓名) 不能为空。已跳过。")
                    continue

                # Validate semester name match
                if excel_semester_name != semester_name_from_db:
                    error_messages.append(
                        f"Row {index + 2}: Excel中的学期名称 '{excel_semester_name}' 与选定的学期 '{semester_name_from_db}' 不匹配。已跳过。")
                    continue

                # Get Major ID
                major_id = get_id_from_name(cur, 'majors', 'name', major_name)
                if major_id is None:
                    error_messages.append(f"Row {index + 2}: 专业 '{major_name}' 未找到。已跳过。")
                    continue

                # Validate and get Total Sessions
                if pd.isna(total_sessions_raw) or not isinstance(total_sessions_raw,
                                                                 (int, float)) or total_sessions_raw < 0:
                    error_messages.append(
                        f"Row {index + 2}: 课程 '{course_name}' 的总课时 '{total_sessions_raw}' 无效。必须是非负整数。已跳过。")
                    continue
                total_sessions = int(total_sessions_raw)

                # Get Course ID (create if not exists, update if exists)
                cur.execute("SELECT id FROM courses WHERE name = %s", (course_name,))
                course_result = cur.fetchone()
                course_id = None
                if course_result:
                    course_id = course_result[0]
                    # Check if update is needed before executing UPDATE
                    cur.execute("SELECT total_sessions, course_type FROM courses WHERE id = %s", (course_id,))
                    current_course_info = cur.fetchone()
                    if current_course_info and (
                            current_course_info[0] != total_sessions or current_course_info[1] != course_type):
                        cur.execute(
                            "UPDATE courses SET total_sessions = %s, course_type = %s WHERE id = %s",
                            (total_sessions, course_type, course_id)
                        )
                        if cur.rowcount > 0: updated_courses_count += 1
                else:
                    cur.execute(
                        "INSERT INTO courses (name, total_sessions, course_type) VALUES (%s, %s, %s) RETURNING id",
                        (course_name, total_sessions, course_type)
                    )
                    course_id = cur.fetchone()[0]
                    created_courses_count += 1

                # Get Teacher ID (Need user_id first)
                user_id = get_id_from_name(cur, 'users', 'username', teacher_name, id_column='id',
                                           additional_conditions={'role': 'teacher'})
                if user_id is None:
                    error_messages.append(
                        f"Row {index + 2}: 教师 '{teacher_name}' (角色: Teacher) 未在 users 表中找到。已跳过。")
                    continue
                # Then get teacher_id from teachers table using user_id
                teacher_id = get_id_from_name(cur, 'teachers', 'user_id', user_id, id_column='id')
                if teacher_id is None:
                    error_messages.append(
                        f"Row {index + 2}: 教师 '{teacher_name}' (User ID: {user_id}) 未在 teachers 表中找到 (可能未关联到用户)。已跳过。")
                    continue

                # Validate and get Expected Students
                if pd.isna(expected_students_raw) or not isinstance(expected_students_raw,
                                                                    (int, float)) or expected_students_raw < 0:
                    error_messages.append(
                        f"Row {index + 2}: 课程 '{course_name}' 的预计学生人数 '{expected_students_raw}' 无效。必须是非负整数。已跳过。")
                    continue
                expected_students = int(expected_students_raw)

                # Determine is_core_course boolean value
                is_core_course = is_core_course_str in ['是', 'yes', 'true', '1']  # Handle common values

                # Add to batch insert list
                course_assignments_to_insert.append(
                    (major_id, course_id, teacher_id, semester_id_from_form, is_core_course, expected_students)
                )

            except Exception as row_error:
                # Log the specific row error but continue processing
                app.logger.error(f"Error processing Excel row {index + 2}: {row_error}", exc_info=True)
                error_messages.append(
                    f"处理 Excel 行 {index + 2} 时发生错误: {row_error}。已跳过。")
                continue  # Continue to the next row

        # Perform batch insert for course assignments
        if course_assignments_to_insert:
            insert_query_ca = """
            INSERT INTO course_assignments (major_id, course_id, teacher_id, semester_id, is_core_course, expected_students)
            VALUES %s
            """
            try:
                execute_values(cur, insert_query_ca, course_assignments_to_insert, page_size=100)
                inserted_assignments_count = len(course_assignments_to_insert)
            except psycopg2.IntegrityError as ie:
                # Handle potential integrity issues during batch insert (e.g. duplicate assignment if UNIQUE constraint exists)
                app.logger.error(f"Integrity error during batch insert: {ie}", exc_info=True)
                error_messages.append(f"批量插入课程计划时发生数据库完整性错误: {ie}。部分或全部数据可能未导入。")
                # Depending on requirements, you might want to rollback and stop, or try inserting row by row here
                # For simplicity, we just add error and proceed with commit/rollback
            except Exception as batch_err:
                app.logger.error(f"Unexpected error during batch insert: {batch_err}", exc_info=True)
                error_messages.append(f"批量插入课程计划时发生未知错误: {batch_err}。部分或全部数据可能未导入。")

        conn.commit()  # Commit the transaction

        summary_message = f"文件处理完成。处理了 {processed_rows} 行 Excel 数据。\n"
        summary_message += f"新建课程: {created_courses_count} 个。\n"
        summary_message += f"更新现有课程信息: {updated_courses_count} 个。\n"
        summary_message += f"导入课程计划条目: {inserted_assignments_count} 条 (已覆盖学期 ID {semester_id_from_form} 的旧数据)。\n"

        if error_messages:
            summary_message += "\n处理过程中遇到以下问题 (部分行可能已跳过):\n" + "\n".join(error_messages)
            # Use status code 207 (Multi-Status) to indicate partial success
            return jsonify({"message": summary_message, "status": "partial_success"}), 207
        else:
            return jsonify({"message": summary_message, "status": "success"}), 200

    except pd.errors.EmptyDataError:
        if conn: conn.rollback()
        return jsonify({"message": "上传的 Excel 文件为空或无法解析。"}), 400
    except (KeyError, ValueError, TypeError) as data_err:  # Catch errors related to data reading/conversion
        if conn: conn.rollback()
        app.logger.error(f"Data error processing Excel file: {data_err}", exc_info=True)
        return jsonify({"message": f"Excel 文件数据格式错误: {data_err}。请检查列名和数据类型。"}), 400
    except psycopg2.Error as db_err:
        if conn: conn.rollback()
        app.logger.error(f"Database operation error during Excel import: {db_err}", exc_info=True)
        return jsonify({"message": f"数据库操作失败: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Unknown error processing Excel file: {e}", exc_info=True)
        return jsonify({"message": f"服务器内部错误: {e}"}), 500
    finally:
        if cur: cur.close()
        if conn:
            conn.autocommit = True  # Restore default autocommit behavior if needed, or just close
            conn.close()


@app.route('/api/course-plans/template', methods=['GET'])
def download_template():
    try:
        output = io.BytesIO()
        # Ensure openpyxl or xlsxwriter is installed: pip install openpyxl xlsxwriter
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            template_columns = [
                '学期名称', '专业名称', '课程名称', '总课时',
                '课程类型', '授课教师姓名', '是否核心课程', '预计学生人数'
            ]
            # Create a DataFrame to define columns. Add a sample row for guidance.
            sample_data = {
                '学期名称': ['例如: 2023-2024学年秋季'],
                '专业名称': ['例如: 计算机科学与技术'],
                '课程名称': ['例如: 数据结构'],
                '总课时': [64],
                '课程类型': ['理论课'],
                '授课教师姓名': ['例如: 张三 (用户系统中的教师名)'],
                '是否核心课程': ['是'],  # 或 否, 1/0, TRUE/FALSE
                '预计学生人数': [80]
            }
            df_template = pd.DataFrame(sample_data)

            # Use the specified columns for the final template, in case sample data changed order
            df_template = df_template[template_columns]

            df_template.to_excel(writer, sheet_name='课程计划模板', index=False)

            # Optional: Auto-fit column widths
            worksheet = writer.sheets['课程计划模板']
            for idx, col in enumerate(df_template.columns):
                # Estimate column width based on header and sample data
                max_len = max((
                    df_template[col].astype(str).map(len).max() if not df_template.empty else 0,
                    len(str(col))
                )) + 2  # Add a little extra padding
                worksheet.set_column(idx, idx, max_len)

        output.seek(0)  # Rewind the buffer to the beginning
        # Flask < 2.3 uses filename/attachment_filename, Flask >= 2.3 uses download_name
        # For broader compatibility, use download_name if available, otherwise attachment_filename
        # Flask 2.3+ is recommended.
        send_file_kwargs = {
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'as_attachment': True,
            'download_name': 'course_plan_template.xlsx'  # Flask >= 2.3
            # 'attachment_filename': 'course_plan_template.xlsx' # Flask < 2.3 - Use one or the other
        }
        # Check Flask version if necessary to pick download_name vs attachment_filename
        # from flask import __version__
        # if version.parse(__version__) < version.parse('2.3'):
        #     send_file_kwargs['attachment_filename'] = send_file_kwargs.pop('download_name')

        return send_file(
            output,
            **send_file_kwargs
        )
    except ImportError:
        # Check for necessary libraries
        app.logger.error("Missing openpyxl or xlsxwriter library for Excel export.")
        return jsonify({"message": "导出功能不可用：缺少 Excel 处理库 (如 openpyxl)。请联系管理员。"}), 501
    except Exception as e:
        app.logger.error(f"Error generating template: {e}", exc_info=True)
        return jsonify({"message": "生成模板失败"}), 500


@app.route('/api/course-plans/<int:plan_id>', methods=['DELETE'])
def delete_course_plan(plan_id):
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor()
        conn.autocommit = True  # Delete is a single operation, autocommit is fine

        # Optional: Check if plan exists before attempting delete
        # cur.execute("SELECT id FROM course_assignments WHERE id = %s", (plan_id,))
        # if cur.fetchone() is None:
        #     return jsonify({"message": "课程计划未找到"}), 404

        cur.execute("DELETE FROM course_assignments WHERE id = %s", (plan_id,))

        # Note: If course_assignments table has foreign keys with ON DELETE CASCADE
        # to timetable_entries, associated timetable entries will be deleted automatically.
        # If not, you might need to manually delete them first depending on your schema design
        # and desired behavior. Your provided schema has ON DELETE CASCADE from timetable_entries.assignment_id
        # to course_assignments.id, which means deleting a *plan* will *cascade delete* *entries* linked to it.

        # conn.commit() # Not needed if autocommit is True

        if cur.rowcount > 0:
            return jsonify({"message": f"课程计划 {plan_id} 删除成功"}), 200
        else:
            # If rowcount is 0, the row didn't exist or wasn't deleted
            return jsonify({"message": "删除失败，课程计划可能不存在或已被删除"}), 404

    except psycopg2.Error as db_err:
        # if conn and not conn.autocommit: conn.rollback() # Rollback only if not autocommit
        app.logger.error(f"DB error deleting course plan {plan_id}: {db_err}", exc_info=True)
        return jsonify({"message": f"数据库操作失败: {db_err}"}), 500
    except Exception as e:
        # if conn and not conn.autocommit: conn.rollback() # Rollback only if not autocommit
        app.logger.error(f"Error deleting course plan {plan_id}: {e}", exc_info=True)
        return jsonify({"message": f"服务器内部错误: {e}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route('/api/majors-list', methods=['GET'])
def get_majors_list():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, name FROM majors ORDER BY name")
        majors = cur.fetchall()
        return jsonify(majors), 200
    except psycopg2.Error as e:
        app.logger.error(f"DB error fetching majors list: {e}", exc_info=True)
        return jsonify({"message": "获取专业列表失败"}), 500
    except Exception as e:
        app.logger.error(f"Error fetching majors list: {e}", exc_info=True)
        return jsonify({"message": "服务器内部错误"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route('/api/teachers-list', methods=['GET'])
def get_teachers_list():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor(cursor_factory=RealDictCursor)
        query = """
        SELECT t.id, u.username AS name
        FROM teachers t
        JOIN users u ON t.user_id = u.id
        WHERE u.role = 'teacher'
        ORDER BY u.username;
        """
        cur.execute(query)
        teachers = cur.fetchall()
        return jsonify(teachers), 200
    except psycopg2.Error as e:
        app.logger.error(f"DB error fetching teachers list: {e}", exc_info=True)
        return jsonify({"message": "获取教师列表失败"}), 500
    except Exception as e:
        app.logger.error(f"Error fetching teachers list: {e}", exc_info=True)
        return jsonify({"message": "服务器内部错误"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


@app.route('/api/course-plans', methods=['POST'])  # 手动添加功能
def add_course_plan():
    data = request.get_json()
    if not data:
        return jsonify({"message": "请求体不能为空"}), 400

    required_fields = ['semester_id', 'major_id', 'course_name', 'total_sessions',
                       'course_type', 'teacher_id', 'is_core_course', 'expected_students']
    # Check if keys exist AND values are not None (get() method returns None if key is missing)
    missing = [field for field in required_fields if data.get(field) is None]
    if missing:
        return jsonify({"message": f"缺少必需的字段: {', '.join(missing)}"}), 400

    course_name = str(data.get('course_name', '')).strip()
    if not course_name: return jsonify({"message": "课程名称不能为空"}), 400

    # Data type validation
    try:
        semester_id = int(data['semester_id'])
        major_id = int(data['major_id'])
        teacher_id = int(data['teacher_id'])
        total_sessions = int(data['total_sessions'])
        expected_students = int(data['expected_students'])
        is_core_course = bool(data['is_core_course'])  # Convert to boolean

        if total_sessions < 0 or expected_students < 0:
            return jsonify({"message": "总课时和预计学生人数必须是非负整数"}), 400
    except (ValueError, TypeError) as e:
        app.logger.warning(f"Data type validation failed for add_course_plan: {e}")
        return jsonify({"message": "部分字段数据格式不正确，请检查整数和布尔值"}), 400

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor()
        conn.autocommit = False  # Start transaction

        # Find or create course
        cur.execute("SELECT id FROM courses WHERE name = %s", (course_name,))
        course_result = cur.fetchone()
        course_id = None

        if course_result:
            course_id = course_result[0]
            # Optionally update course details if they differ (matching upload logic)
            cur.execute(
                "UPDATE courses SET total_sessions = %s, course_type = %s WHERE id = %s AND (total_sessions != %s OR course_type != %s)",
                (total_sessions, data['course_type'], course_id, total_sessions, data['course_type'])
            )
            # No count needed for manual add, just ensure the course details are up-to-date
        else:
            cur.execute(
                "INSERT INTO courses (name, total_sessions, course_type) VALUES (%s, %s, %s) RETURNING id",
                (course_name, total_sessions, data['course_type'])
            )
            course_id = cur.fetchone()[0]

        # Insert course assignment
        insert_query = """
        INSERT INTO course_assignments
            (major_id, course_id, teacher_id, semester_id, is_core_course, expected_students)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
        """
        cur.execute(insert_query, (
            major_id, course_id, teacher_id, semester_id,
            is_core_course, expected_students
        ))
        new_plan_id = cur.fetchone()[0]
        conn.commit()

        return jsonify({
            "message": "课程计划添加成功",
            "plan_id": new_plan_id,
            "course_id": course_id  # Return course_id as well for frontend reference
        }), 201

    except psycopg2.IntegrityError as e:
        if conn: conn.rollback()
        # Check error details to provide more specific feedback if possible
        # E.g., unique violation on course_assignments if you add that constraint later
        error_detail = str(e)
        msg = f"数据库完整性错误。请检查选定的专业/教师/学期ID是否有效，或是否存在重复的课程计划。详情: {error_detail}"
        app.logger.warning(f"Integrity error adding course plan: {e}", exc_info=True)
        return jsonify({"message": msg}), 409
    except psycopg2.Error as db_err:
        if conn: conn.rollback()
        app.logger.error(f"DB error adding course plan: {db_err}", exc_info=True)
        return jsonify({"message": f"数据库操作失败: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Error adding course plan: {e}", exc_info=True)
        return jsonify({"message": f"服务器内部错误: {e}"}), 500
    finally:
        if cur: cur.close()
        if conn:
            conn.autocommit = True
            conn.close()


@app.route('/api/course-plans/<int:plan_id>', methods=['PUT'])  # 编辑功能
def update_course_plan(plan_id):
    data = request.get_json()
    if not data:
        return jsonify({"message": "请求体不能为空"}), 400

    # semester_id is usually fixed for an existing assignment, course_id is derived
    required_fields = ['major_id', 'course_name', 'total_sessions', 'course_type',
                       'teacher_id', 'is_core_course', 'expected_students']
    missing = [field for field in required_fields if data.get(field) is None]  # Check for None
    if missing:
        return jsonify({"message": f"缺少必需的字段: {', '.join(missing)}"}), 400

    course_name_new = str(data.get('course_name', '')).strip()
    if not course_name_new: return jsonify({"message": "课程名称不能为空"}), 400

    # Data type validation
    try:
        major_id = int(data['major_id'])
        teacher_id = int(data['teacher_id'])
        total_sessions = int(data['total_sessions'])
        expected_students = int(data['expected_students'])
        is_core_course = bool(data['is_core_course'])  # Convert to boolean

        if total_sessions < 0 or expected_students < 0:
            return jsonify({"message": "总课时和预计学生人数必须是非负整数"}), 400
    except (ValueError, TypeError) as e:
        app.logger.warning(f"Data type validation failed for update_course_plan {plan_id}: {e}")
        return jsonify({"message": "部分字段数据格式不正确，请检查整数和布尔值"}), 400

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor()
        conn.autocommit = False  # Start transaction

        # Get the original course_id linked to this assignment
        cur.execute("SELECT course_id, semester_id FROM course_assignments WHERE id = %s", (plan_id,))
        assignment_data = cur.fetchone()
        if not assignment_data:
            conn.rollback()
            return jsonify({"message": "待编辑的课程计划未找到"}), 404
        original_course_id = assignment_data[0]
        semester_id = assignment_data[1]  # Keep semester_id consistent

        # Find or create the potentially new course if the name changed (or update existing)
        # This logic is tricky. If the user changes the course name, should it create a new course
        # or rename the existing one? Renaming the existing one is simpler for this context.
        # If the *new* course name already exists and refers to a *different* course,
        # this logic would need refinement (e.g., linking to the existing course and possibly cleaning up the old one).
        # For now, assuming renaming the linked course is acceptable behavior for edit.

        # Update the associated course's details in the 'courses' table
        cur.execute(
            """
            UPDATE courses
            SET name = %s, total_sessions = %s, course_type = %s
            WHERE id = %s
            """,
            (course_name_new, total_sessions, data['course_type'], original_course_id)
        )
        # course_id in course_assignments remains original_course_id

        # Update the 'course_assignments' table
        update_query_ca = """
        UPDATE course_assignments SET
            major_id = %s,
            teacher_id = %s,
            is_core_course = %s,
            expected_students = %s
            -- course_id and semester_id are not typically updated here
        WHERE id = %s;
        """
        cur.execute(update_query_ca, (
            major_id, teacher_id, is_core_course,
            expected_students, plan_id
        ))

        # Check if the assignment was actually updated (e.g., if plan_id was valid)
        if cur.rowcount == 0:
            conn.rollback()  # Rollback course update too
            # This case should ideally be caught by the initial SELECT check, but good to double check
            return jsonify({"message": "更新失败，课程计划未找到或数据未改变"}), 404  # Return 404 or 200 with message
            # If you want to return 200 when data is unchanged, check cur.rowcount AND course update rowcount

        conn.commit()
        return jsonify({"message": f"课程计划 {plan_id} 更新成功"}), 200

    except psycopg2.IntegrityError as e:
        if conn: conn.rollback()
        error_detail = str(e)
        msg = f"数据库完整性错误。请检查选定的专业/教师ID是否有效。详情: {error_detail}"
        app.logger.warning(f"Integrity error updating course plan {plan_id}: {e}", exc_info=True)
        return jsonify({"message": msg}), 409
    except psycopg2.Error as db_err:
        if conn: conn.rollback()
        app.logger.error(f"DB error updating course plan {plan_id}: {db_err}", exc_info=True)
        return jsonify({"message": f"数据库操作失败: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Error updating course plan {plan_id}: {e}", exc_info=True)
        return jsonify({"message": f"服务器内部错误: {e}"}), 500
    finally:
        if cur: cur.close()
        if conn:
            conn.autocommit = True
            conn.close()


# Route to trigger the scheduling algorithm
@app.route('/api/schedule/run/<int:semester_id>', methods=['POST'])
def run_scheduling_for_semester_api(semester_id):
    app.logger.info(f"API: Received request to run scheduling for semester_id: {semester_id}")
    try:
        # Pass the app's get_db_connection function to the scheduler module
        # The scheduler module should handle connecting, fetching data, running algo, saving results, disconnecting
        scheduling_summary = scheduler_module.run_full_scheduling_process(semester_id, get_db_connection)

        app.logger.info(
            f"API: Scheduling for semester {semester_id} finished. Status: {scheduling_summary.get('status')}")

        status = scheduling_summary.get("status", "failure").lower()
        message = scheduling_summary.get("message", "排课已执行。")
        summary = scheduling_summary.get("summary", {})  # Ensure summary is included

        if status.startswith("success"):
            # Successfully ran, even if some constraints weren't met (might be partial success)
            # scheduler_module should indicate if it's partial or full success
            return jsonify({
                "message": message,
                "summary": summary
            }), 200  # Or 207 for partial success if scheduler_module indicates that
        else:
            # Indicates a failure in the scheduling *process* (e.g., data loading failed, algorithm crashed)
            return jsonify({
                "message": message,
                "summary": summary
            }), 500  # Internal server error related to scheduling process


    except Exception as e:
        # Catch any unexpected errors during the API call itself
        app.logger.error(f"API: Error during scheduling for semester {semester_id}: {e}", exc_info=True)
        # Avoid returning sensitive exception details to the client
        return jsonify({"message": f"执行排课时发生内部错误。"}), 500


# API to get timetable data for a whole semester
@app.route('/api/timetables/semester/<int:semester_id>', methods=['GET'])
def get_semester_timetable(semester_id):
    conn = None
    cur = None  # Ensure cur is initialized to None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor(cursor_factory=RealDictCursor)  # Or DictCursor

        # Use time_slots based on your schema
        query = """
        SELECT
            te.id, te.week_number, te.assignment_id,
            s.name as semester_name,
            m.id as major_id, m.name as major_name,
            c.id as course_id, c.name as course_name, c.course_type,
            u.username as teacher_name, t.id as teacher_id,
            cl.id as classroom_id, cl.building || '-' || cl.room_number as classroom_name, -- Concatenate building and room
            ts.id as timeslot_id, ts.day_of_week, ts.period, ts.start_time, ts.end_time -- TIME fields
        FROM timetable_entries te
        JOIN semesters s ON te.semester_id = s.id
        JOIN majors m ON te.major_id = m.id
        JOIN courses c ON te.course_id = c.id
        JOIN teachers t ON te.teacher_id = t.id
        JOIN users u ON t.user_id = u.id -- Join to get teacher username
        JOIN classrooms cl ON te.classroom_id = cl.id
        JOIN time_slots ts ON te.timeslot_id = ts.id -- Correct table name
        WHERE te.semester_id = %s
        ORDER BY te.major_id, te.week_number, ts.day_of_week, ts.period;
        """
        cur.execute(query, (semester_id,))

        fetched_entries = cur.fetchall()

        # --- FIX: Convert datetime.time objects to strings for JSON serialization ---
        entries_for_json = []
        for row in fetched_entries:
            # DictCursor or RealDictCursor rows behave like dicts, convert to plain dict if preferred
            entry = dict(row)

            # Check and convert time objects
            if 'start_time' in entry and isinstance(entry['start_time'], datetime.time):
                entry['start_time'] = entry['start_time'].strftime('%H:%M:%S')

            if 'end_time' in entry and isinstance(entry['end_time'], datetime.time):
                entry['end_time'] = entry['end_time'].strftime('%H:%M:%S')

            entries_for_json.append(entry)
        # --- End of FIX ---

        cur.close()  # Close cursor before potential error handling

        return jsonify(entries_for_json), 200  # Return the converted data

    except psycopg2.Error as e:
        app.logger.error(f"API: DB error fetching timetable for semester {semester_id}: {e}", exc_info=True)
        return jsonify({"message": "获取学期课表数据失败"}), 500  # User-friendly error
    except Exception as e:
        app.logger.error(f"API: An unexpected error occurred fetching semester timetable {semester_id}: {e}",
                         exc_info=True)
        return jsonify({"message": f"获取学期课表数据时发生内部错误"}), 500  # User-friendly error
    finally:
        # Ensure cursor and connection are closed even if errors occur
        if cur: cur.close()
        if conn: conn.close()


# API to export timetable data for a whole semester to Excel#无用
@app.route('/api/timetables/export/semester/<int:semester_id>', methods=['GET'])
def export_semester_timetable_excel(semester_id):
    try:
        # load_data_from_db is expected to get all necessary lookup data (semesters, majors, etc.)
        all_data = scheduler_module.load_data_from_db(get_db_connection)
        current_semester = all_data.get('semesters', {}).get(semester_id)  # Use get with default {} for safety
        if not current_semester:
            return jsonify({"message": "学期信息未找到，无法导出"}), 404  # Use 404 if semester ID is bad

        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)  # DictCursor is fine for fetching raw data

        # Fetch raw TimetableEntry compatible data
        # Ensure field names match what scheduler_module.TimetableEntry expects
        cur.execute("""
            SELECT id, semester_id, major_id, course_id, teacher_id, classroom_id, timeslot_id, week_number, assignment_id
            FROM timetable_entries WHERE semester_id = %s
            """, (semester_id,))
        raw_entries = cur.fetchall()
        cur.close()
        conn.close()

        # Convert fetched dicts to TimetableEntry objects (assuming it's a namedtuple/dataclass)
        # This requires scheduler_module.TimetableEntry to accept these fields
        schedule_entries_for_export = [scheduler_module.TimetableEntry(**row) for row in raw_entries]

        # Check if semester has valid week information before proceeding to generate report
        if not current_semester or not hasattr(current_semester, 'total_weeks') or current_semester.total_weeks <= 0:
            # Still try to generate if there are entries, might just have weird output
            if not schedule_entries_for_export:
                return jsonify({"message": "当前学期无排课数据可供导出，或学期周数未设置"}), 404

        # generate_excel_report_for_send_file should handle empty schedule_entries gracefully
        excel_buffer = scheduler_module.generate_excel_report_for_send_file(
            schedule_entries_for_export, all_data, current_semester
        )

        # Sanitize semester name for filename
        # Allow CJK, alphanumeric, hyphen, underscore, space. Replace others with underscore.
        safe_semester_name = re.sub(r'[^\w\u4e00-\u9fff\s\-]', '_', current_semester.name)
        # Remove leading/trailing spaces/underscores just in case
        safe_semester_name = safe_semester_name.strip(' _')
        # Replace spaces with underscores for better filename compatibility
        safe_semester_name = safe_semester_name.replace(' ', '_')

        # Ensure filename is not empty after sanitization
        if not safe_semester_name:
            safe_semester_name = f"semester_{semester_id}"

        filename = f"排课结果_{safe_semester_name}_学期ID{semester_id}.xlsx"

        # Flask < 2.3 uses filename/attachment_filename, Flask >= 2.3 uses download_name
        send_file_kwargs = {
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'as_attachment': True,
            'download_name': filename  # Flask >= 2.3
            # 'attachment_filename': filename # Flask < 2.3
        }
        # Check Flask version if necessary to pick download_name vs attachment_filename

        return send_file(
            excel_buffer,
            **send_file_kwargs
        )
    except ImportError as ie:  # Specifically for openpyxl or xlsxwriter not found
        app.logger.error(f"API Export: Missing Excel library: {ie}", exc_info=True)
        return jsonify({"message": "导出功能不可用：缺少 Excel 处理库 (如 openpyxl)。请联系管理员。"}), 501
    except Exception as e:
        app.logger.error(f"API Export: Error exporting semester timetable for {semester_id}: {e}", exc_info=True)
        return jsonify({"message": f"导出Excel失败: {str(e)}"}), 500  # Return generic error, log details


# API to get timetable data for a specific teacher and semester
@app.route('/api/timetables/teacher/<int:teacher_id>/semester/<int:semester_id>', methods=['GET'])
def get_teacher_timetable(teacher_id, semester_id):
    conn = None
    cur = None  # Ensure cur is initialized to None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor(cursor_factory=RealDictCursor)  # Or DictCursor
        # Use time_slots based on your schema
        query = """
        SELECT te.id, te.week_number, te.assignment_id,
               s.name as semester_name,
               m.id as major_id, m.name as major_name,
               c.id as course_id, c.name as course_name, c.course_type,
               u.username as teacher_name, t.id as teacher_id,
               cl.id as classroom_id, cl.building || '-' || cl.room_number as classroom_name,
               ts.id as timeslot_id, ts.day_of_week, ts.period, ts.start_time, ts.end_time -- TIME fields
        FROM timetable_entries te
        JOIN semesters s ON te.semester_id = s.id
        JOIN majors m ON te.major_id = m.id
        JOIN courses c ON te.course_id = c.id
        JOIN teachers t ON te.teacher_id = t.id
        JOIN users u ON t.user_id = u.id
        JOIN classrooms cl ON te.classroom_id = cl.id
        JOIN time_slots ts ON te.timeslot_id = ts.id -- Correct table name
        WHERE te.semester_id = %s AND te.teacher_id = %s
        ORDER BY te.week_number, ts.day_of_week, ts.period;
        """
        cur.execute(query, (semester_id, teacher_id))

        fetched_entries = cur.fetchall()

        # --- FIX: Convert datetime.time objects to strings for JSON serialization ---
        entries_for_json = []
        for row in fetched_entries:
            entry = dict(row)

            if 'start_time' in entry and isinstance(entry['start_time'], datetime.time):
                entry['start_time'] = entry['start_time'].strftime('%H:%M:%S')

            if 'end_time' in entry and isinstance(entry['end_time'], datetime.time):
                entry['end_time'] = entry['end_time'].strftime('%H:%M:%S')

            entries_for_json.append(entry)
        # --- End of FIX ---

        cur.close()  # Close cursor

        return jsonify(entries_for_json), 200  # Return converted data

    except psycopg2.Error as e:
        app.logger.error(f"API: DB error fetching timetable for teacher {teacher_id}, semester {semester_id}: {e}",
                         exc_info=True)
        return jsonify({"message": "获取教师课表数据失败"}), 500  # User-friendly error
    except Exception as e:
        app.logger.error(
            f"API: An unexpected error occurred fetching teacher timetable {teacher_id}, semester {semester_id}: {e}",
            exc_info=True)
        return jsonify({"message": f"获取教师课表数据时发生内部错误"}), 500  # User-friendly error
    finally:
        if cur: cur.close()
        if conn: conn.close()


# API to export timetable data for a specific teacher and semester to Excel
@app.route('/api/timetables/export/teacher/<int:teacher_id>/semester/<int:semester_id>', methods=['GET'])
def export_teacher_timetable_excel(teacher_id, semester_id):
    try:
        all_data = scheduler_module.load_data_from_db(get_db_connection)
        current_semester = all_data.get('semesters', {}).get(semester_id)
        teacher_info = all_data.get('teachers', {}).get(teacher_id)  # Assuming teachers dict is keyed by id
        if not current_semester or not teacher_info:
            return jsonify({"message": "学期或教师信息未找到，无法导出"}), 404

        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT id, semester_id, major_id, course_id, teacher_id, classroom_id, timeslot_id, week_number, assignment_id
            FROM timetable_entries WHERE semester_id = %s AND teacher_id = %s
            """, (semester_id, teacher_id))
        raw_entries = cur.fetchall()
        cur.close()
        conn.close()
        schedule_entries_for_export = [scheduler_module.TimetableEntry(**row) for row in raw_entries]

        if not current_semester or not hasattr(current_semester, 'total_weeks') or current_semester.total_weeks <= 0:
            if not schedule_entries_for_export:
                return jsonify({"message": "当前学期或指定教师无排课数据可供导出"}), 404

        excel_buffer = scheduler_module.generate_excel_report_for_send_file(
            schedule_entries_for_export, all_data, current_semester, target_teacher_id=teacher_id
        )

        safe_teacher_name = re.sub(r'[^\w\u4e00-\u9fff\s\-]', '_',
                                   teacher_info.name if hasattr(teacher_info, 'name') else str(
                                       teacher_id))  # Fallback to ID
        safe_teacher_name = safe_teacher_name.strip(' _').replace(' ', '_')
        if not safe_teacher_name: safe_teacher_name = f"teacher_{teacher_id}"

        safe_semester_name = re.sub(r'[^\w\u4e00-\u9fff\s\-]', '_', current_semester.name)
        safe_semester_name = safe_semester_name.strip(' _').replace(' ', '_')
        if not safe_semester_name: safe_semester_name = f"semester_{semester_id}"

        filename = f"教师课表_{safe_teacher_name}_{safe_semester_name}.xlsx"

        send_file_kwargs = {
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'as_attachment': True,
            'download_name': filename  # Flask >= 2.3
            # 'attachment_filename': filename # Flask < 2.3
        }
        # Check Flask version if necessary

        return send_file(excel_buffer, **send_file_kwargs)
    except ImportError:
        app.logger.error("Missing openpyxl or xlsxwriter library for Excel export.")
        return jsonify({"message": "导出功能不可用：缺少 Excel 处理库 (如 openpyxl)。"}), 501
    except Exception as e:
        app.logger.error(f"API Export: Error exporting teacher timetable: {e}", exc_info=True)
        return jsonify({"message": f"导出教师课表Excel失败: {str(e)}"}), 500


# API to get timetable data for a specific major and semester
# ... (其他 Flask 路由)

@app.route('/api/timetables/major/<int:major_id>/semester/<int:semester_id>', methods=['GET'])
def get_major_timetable(major_id, semester_id):
    # 从查询参数中获取周数，如果未提供则为 None
    # 使用 request.args.get('week', type=int) 来获取并尝试转换为整数
    # 如果 'week' 参数不存在或无法转换，selected_week 将是 None
    selected_week = request.args.get('week', type=int, default=None)
    app.logger.debug(f"API called: /api/timetables/major/{major_id}/semester/{semester_id}")
    app.logger.debug(f"Received 'week' parameter: {selected_week} (Type: {type(selected_week)})")
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        # 使用 DictCursor 或 RealDictCursor 以便按列名访问
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 基础查询语句，连接必要的表以获取所需信息
        # 注意：你的原始查询缺少了 JOIN courses, teachers, users, classrooms 获取名称的部分，这里补上
        query = """
            SELECT
                te.id,
                te.semester_id,
                te.major_id,
                te.course_id,
                te.teacher_id,
                te.classroom_id,
                te.timeslot_id,
                te.week_number,
                te.assignment_id,
                ts.day_of_week,
                ts.period, -- 保留 period 用于排序和定位单元格
                ts.start_time,
                ts.end_time,
                c.name as course_name,
                c.course_type, -- 添加课程类型
                u.username as teacher_name,
                cl.building || '-' || cl.room_number as classroom_name, -- classroom_name 已在你的原代码中
                m.name as major_name -- 如果需要显示专业名（虽然在此视图可能不需要）
            FROM timetable_entries te
            JOIN time_slots ts ON te.timeslot_id = ts.id
            JOIN courses c ON te.course_id = c.id
            JOIN teachers t ON te.teacher_id = t.id
            JOIN users u ON t.user_id = u.id
            JOIN classrooms cl ON te.classroom_id = cl.id
            JOIN majors m ON te.major_id = m.id -- 加入 majors 表
            WHERE te.major_id = %s AND te.semester_id = %s
        """
        params = [major_id, semester_id]
        if selected_week is not None:
            app.logger.debug(f"Applying week filter: week_number = {selected_week}")
        # 如果提供了 week 参数，则添加到查询条件中
        if selected_week is not None:
            # 检查 week_number 是否大于 0，防止无效查询
            if selected_week > 0:
                query += " AND te.week_number = %s"
                params.append(selected_week)
            else:
                # 如果提供了无效周数 (如 0 或负数)，返回空结果比较安全
                app.logger.warning(f"Invalid week number requested: {selected_week}")
                return jsonify([]), 200 # 或者返回错误信息

        # 添加排序，确保课表顺序正确 (按天、按节次)
        query += " ORDER BY ts.day_of_week, ts.period;" # 使用 time_slots 的 period 排序
        app.logger.debug(f"Final SQL query: {query}")
        app.logger.debug(f"Query parameters: {tuple(params)}")
        cur.execute(query, tuple(params)) # 将参数列表转为元组

        fetched_entries = cur.fetchall()
        app.logger.debug(f"Fetched {len(fetched_entries)} entries from database.")  # <--- 这行
        # --- 时间格式转换 ---
        entries_for_json = []
        for row in fetched_entries:
            # RealDictCursor 返回的是类字典对象，直接用或转成普通 dict
            entry = dict(row)
            if 'start_time' in entry and isinstance(entry['start_time'], datetime.time):
                entry['start_time'] = entry['start_time'].strftime('%H:%M:%S')
            if 'end_time' in entry and isinstance(entry['end_time'], datetime.time):
                entry['end_time'] = entry['end_time'].strftime('%H:%M:%S')
            entries_for_json.append(entry)
        # --- 结束转换 ---

        cur.close()
        app.logger.debug(f"Returning {len(entries_for_json)} entries in JSON response.")
        return jsonify(entries_for_json), 200

    except psycopg2.Error as e:
        app.logger.error(f"Database error fetching timetable for major {major_id} semester {semester_id} week {selected_week}: {e}", exc_info=True)
        return jsonify({"message": "获取专业课表数据失败"}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error fetching major timetable major {major_id} semester {semester_id} week {selected_week}: {e}", exc_info=True)
        return jsonify({"message": "获取专业课表数据时发生内部错误"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()



# API to export timetable data for a specific major and semester to Excel
@app.route('/api/timetables/export/major/<int:major_id>/semester/<int:semester_id>', methods=['GET'])
def export_major_timetable_excel(major_id, semester_id):
    try:
        all_data = scheduler_module.load_data_from_db(get_db_connection)
        current_semester = all_data.get('semesters', {}).get(semester_id)
        major_info = all_data.get('majors', {}).get(major_id)  # Assuming majors dict is keyed by id
        if not current_semester or not major_info:
            return jsonify({"message": "学期或专业信息未找到，无法导出"}), 404

        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("""
            SELECT id, semester_id, major_id, course_id, teacher_id, classroom_id, timeslot_id, week_number, assignment_id
            FROM timetable_entries WHERE semester_id = %s AND major_id = %s
            """, (semester_id, major_id))
        raw_entries = cur.fetchall()
        cur.close()
        conn.close()
        schedule_entries_for_export = [scheduler_module.TimetableEntry(**row) for row in raw_entries]

        if not current_semester or not hasattr(current_semester, 'total_weeks') or current_semester.total_weeks <= 0:
            if not schedule_entries_for_export:
                return jsonify({"message": "当前学期或指定专业无排课数据可供导出"}), 404

        excel_buffer = scheduler_module.generate_excel_report_for_send_file(
            schedule_entries_for_export, all_data, current_semester, target_major_id=major_id
        )

        safe_major_name = re.sub(r'[^\w\u4e00-\u9fff\s\-]', '_',
                                 major_info.name if hasattr(major_info, 'name') else str(major_id))
        safe_major_name = safe_major_name.strip(' _').replace(' ', '_')
        if not safe_major_name: safe_major_name = f"major_{major_id}"

        safe_semester_name = re.sub(r'[^\w\u4e00-\u9fff\s\-]', '_', current_semester.name)
        safe_semester_name = safe_semester_name.strip(' _').replace(' ', '_')
        if not safe_semester_name: safe_semester_name = f"semester_{semester_id}"

        filename = f"专业课表_{safe_major_name}_{safe_semester_name}.xlsx"

        send_file_kwargs = {
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'as_attachment': True,
            'download_name': filename  # Flask >= 2.3
            # 'attachment_filename': filename # Flask < 2.3
        }
        # Check Flask version if necessary

        return send_file(excel_buffer, **send_file_kwargs)
    except ImportError:
        app.logger.error("Missing openpyxl or xlsxwriter library for Excel export.")
        return jsonify({"message": "导出功能不可用：缺少 Excel 处理库 (如 openpyxl)。"}), 501
    except Exception as e:
        app.logger.error(f"API Export: Error exporting major timetable: {e}", exc_info=True)
        return jsonify({"message": f"导出专业课表Excel失败: {str(e)}"}), 500

#学生登录用
@app.route('/api/timetables/student/<int:user_id>/semester/<int:semester_id>', methods=['GET'])
def get_student_timetable(user_id, semester_id):
    """
    Fetches timetable entries for a specific student (identified by user_id),
    a specific semester, and optionally a specific week.
    """
    # Get week from query parameters
    selected_week = request.args.get('week', type=int, default=None)
    app.logger.debug(f"API called: /api/timetables/student/{user_id}/semester/{semester_id}")
    app.logger.debug(f"Received 'week' parameter: {selected_week} (Type: {type(selected_week)})")

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor(cursor_factory=RealDictCursor) # Or DictCursor

        # 1. Verify user exists and is a student, and get their major_id
        cur.execute("""
            SELECT s.major_id
            FROM students s
            JOIN users u ON s.user_id = u.id
            WHERE u.id = %s AND u.role = 'student'
        """, (user_id,))
        student_info = cur.fetchone()

        if not student_info:
            # User not found, or not a student, or student record missing
            app.logger.warning(f"Attempted to get student timetable for user_id {user_id}, but user not found as a student or major not linked.")
            return jsonify({"message": "未找到您的学生信息或未指定专业，无法获取课表。"}), 404

        student_major_id = student_info['major_id']

        # 2. Fetch timetable entries using the student's major_id, semester_id, and week filter
        query = """
            SELECT
                te.id, te.semester_id, te.major_id, te.course_id, te.teacher_id, te.classroom_id, te.timeslot_id, te.week_number, te.assignment_id,
                ts.day_of_week, ts.period, ts.start_time, ts.end_time,
                c.name as course_name, c.course_type,
                u.username as teacher_name, -- Include teacher name
                cl.building || '-' || cl.room_number as classroom_name
                -- No need for major_name in student view result, but could fetch it if needed
            FROM timetable_entries te
            JOIN time_slots ts ON te.timeslot_id = ts.id
            JOIN courses c ON te.course_id = c.id
            JOIN teachers t ON te.teacher_id = t.id
            JOIN users u ON t.user_id = u.id -- Join to get teacher username
            JOIN classrooms cl ON te.classroom_id = cl.id
            WHERE te.major_id = %s AND te.semester_id = %s
        """
        params = [student_major_id, semester_id]

        if selected_week is not None and selected_week > 0:
             app.logger.debug(f"Applying week filter: week_number = {selected_week}")
             query += " AND te.week_number = %s"
             params.append(selected_week)
        elif selected_week is not None and selected_week <= 0:
             app.logger.warning(f"Invalid week number requested: {selected_week}. Returning empty.")
             return jsonify([]), 200 # Return empty if week is invalid

        # Add sorting for correct timetable display order
        query += " ORDER BY te.week_number, ts.day_of_week, ts.period;" # Order by week, then day, then period

        app.logger.debug(f"Final SQL query for student timetable: {query}")
        app.logger.debug(f"Query parameters for student timetable: {tuple(params)}")
        cur.execute(query, tuple(params))

        fetched_entries = cur.fetchall()
        app.logger.debug(f"Fetched {len(fetched_entries)} entries for student timetable.")

        # --- Time format conversion ---
        entries_for_json = []
        for row in fetched_entries:
            entry = dict(row) # Convert RealDictRow to dict
            if 'start_time' in entry and isinstance(entry['start_time'], datetime.time):
                entry['start_time'] = entry['start_time'].strftime('%H:%M:%S')
            if 'end_time' in entry and isinstance(entry['end_time'], datetime.time):
                entry['end_time'] = entry['end_time'].strftime('%H:%M:%S')
            entries_for_json.append(entry)
        # --- End conversion ---

        cur.close() # Close cursor

        return jsonify(entries_for_json), 200

    except psycopg2.Error as e:
        app.logger.error(f"Database error fetching student timetable for user {user_id} semester {semester_id} week {selected_week}: {e}", exc_info=True)
        return jsonify({"message": "获取个人课表数据失败"}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error fetching student timetable user {user_id} semester {semester_id} week {selected_week}: {e}", exc_info=True)
        return jsonify({"message": "获取个人课表数据时发生内部错误"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


# --- NEW: Student Timetable Export Endpoint ---
@app.route('/api/timetables/export/student/<int:user_id>/semester/<int:semester_id>', methods=['GET'])
def export_student_timetable_excel(user_id, semester_id):
    """
    Exports the full semester timetable for a specific student (identified by user_id).
    """
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor() # Use basic cursor first

        # 1. Verify user exists and is a student, get major_id and username
        cur.execute("""
            SELECT s.major_id, u.username
            FROM students s
            JOIN users u ON s.user_id = u.id
            WHERE u.id = %s AND u.role = 'student'
        """, (user_id,))
        student_info = cur.fetchone() # student_info will be (major_id, username)

        if not student_info:
            app.logger.warning(f"Attempted export for user_id {user_id}, but user not found as a student or major not linked.")
            return jsonify({"message": "未找到您的学生信息或未指定专业，无法导出课表。"}), 404

        student_major_id = student_info[0]
        student_username = student_info[1]

        # Load all necessary lookup data (including semesters, majors, teachers, etc.)
        # load_data_from_db returns dictionaries keyed by ID, e.g., {'semesters': {id: semester_obj, ...}}
        all_data = scheduler_module.load_data_from_db(get_db_connection) # Pass the connection function

        current_semester = all_data.get('semesters', {}).get(semester_id)
        if not current_semester:
             # This should ideally not happen if semester_id is from frontend selects, but check anyway
             return jsonify({"message": "学期信息未找到，无法导出"}), 404

        # 2. Fetch *all* timetable entries for this student's major and semester
        # Use DictCursor for fetching raw data to pass to TimetableEntry constructor
        cur_dict = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur_dict.execute("""
            SELECT id, semester_id, major_id, course_id, teacher_id, classroom_id, timeslot_id, week_number, assignment_id
            FROM timetable_entries
            WHERE semester_id = %s AND major_id = %s
            ORDER BY week_number, timeslot_id; -- Consistent ordering
            """, (semester_id, student_major_id)) # Filter by student's major_id
        raw_entries = cur_dict.fetchall()
        cur_dict.close() # Close dict cursor

        conn.close() # Close main connection

        if not raw_entries:
            return jsonify({"message": "当前学期无排课数据可供导出，或学期周数未设置"}), 404

        # Convert fetched dicts to TimetableEntry objects (assuming it's a namedtuple/dataclass)
        schedule_entries_for_export = [scheduler_module.TimetableEntry(**row) for row in raw_entries]

        # Generate Excel report. Pass student_major_id or user_id if generate_excel_report_for_send_file
        # needs to filter or format specifically for a student (e.g., hide other majors' data if the raw_entries included them).
        # Given the query filters by major_id, the generator just needs the list and lookup data.
        excel_buffer = scheduler_module.generate_excel_report_for_send_file(
            schedule_entries_for_export, all_data, current_semester
            # Optionally pass target_major_id=student_major_id or other flags if generator logic depends on it
        )

        # Sanitize names for filename
        safe_student_username = re.sub(r'[^\w\u4e00-\u9fff\s\-]', '_', student_username)
        safe_student_username = safe_student_username.strip(' _').replace(' ', '_')
        if not safe_student_username: safe_student_username = f"user_{user_id}"

        safe_semester_name = re.sub(r'[^\w\u4e00-\u9fff\s\-]', '_', current_semester.name)
        safe_semester_name = safe_semester_name.strip(' _').replace(' ', '_')
        if not safe_semester_name: safe_semester_name = f"semester_{semester_id}"

        filename = f"我的课表_{safe_student_username}_{safe_semester_name}_(全学期).xlsx" # Indicate it's full semester

        send_file_kwargs = {
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'as_attachment': True,
            'download_name': filename
        }

        return send_file(excel_buffer, **send_file_kwargs)

    except ImportError as ie:
        app.logger.error(f"API Export: Missing Excel library: {ie}", exc_info=True)
        return jsonify({"message": "导出功能不可用：缺少 Excel 处理库 (如 openpyxl)。请联系管理员。"}), 501
    except Exception as e:
        app.logger.error(f"API Export: Error exporting student timetable for user {user_id}, semester {semester_id}: {e}", exc_info=True)
        return jsonify({"message": f"导出Excel失败: {str(e)}"}), 500
    finally:
        if conn: conn.close() # Ensure connection is closed
# 教师登录用
@app.route('/api/timetables/teacher-dashboard/<int:user_id>/semester/<int:semester_id>', methods=['GET'])
def get_teacher_weekly_timetable(user_id, semester_id):
    """
    获取指定用户(教师)在指定学期指定周次的课表。
    需要查询参数 week=<int:week_number>
    """
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"message": "数据库连接失败"}), 500

        cur = conn.cursor(cursor_factory=RealDictCursor)

        # --- Step 1: Find the teacher_id from user_id ---
        # First, verify the user exists and is a teacher (Good practice)
        cur.execute("SELECT id, role FROM users WHERE id = %s", (user_id,))
        user_info = cur.fetchone()

        if not user_info:
             cur.close()
             return jsonify({"error": "用户不存在"}), 404

        if user_info['role'].lower() != 'teacher':
             cur.close()
             return jsonify({"error": "用户不是教师类型"}), 403 # Forbidden if not a teacher

        # Now find the corresponding teacher_id in the teachers table
        # Note: Assuming a 1-to-1 relationship between users.id and teachers.user_id
        cur.execute("SELECT id FROM teachers WHERE user_id = %s", (user_id,))
        teacher_profile = cur.fetchone()

        if not teacher_profile:
            cur.close()
            return jsonify({"error": "找不到该用户关联的教师档案"}), 404

        teacher_id_from_user = teacher_profile['id'] # Get the actual teacher_id


        # --- Step 2: Get the week number from query parameters ---
        week_number = request.args.get('week', type=int)
        if week_number is None:
            cur.close()
            return jsonify({"error": "缺少周次参数 (week)"}), 400


        # --- Step 3: Execute the SQL query with semester_id, teacher_id, and week_number filtering ---
        # Modify the query to filter by teacher_id and week_number
        query = """
        SELECT te.id, te.week_number, te.assignment_id,
               s.name as semester_name,
               m.id as major_id, m.name as major_name,
               c.id as course_id, c.name as course_name, c.course_type,
               u.username as teacher_name, t.id as teacher_id,
               cl.id as classroom_id, cl.building || '-' || cl.room_number as classroom_name,
               ts.id as timeslot_id, ts.day_of_week, ts.period, ts.start_time, ts.end_time -- TIME fields
        FROM timetable_entries te
        JOIN semesters s ON te.semester_id = s.id
        LEFT JOIN majors m ON te.major_id = m.id -- Use LEFT JOIN for major
        JOIN courses c ON te.course_id = c.id
        JOIN teachers t ON te.teacher_id = t.id
        JOIN users u ON t.user_id = u.id
        LEFT JOIN classrooms cl ON te.classroom_id = cl.id -- Use LEFT JOIN for classroom
        JOIN time_slots ts ON te.timeslot_id = ts.id
        WHERE te.semester_id = %s AND te.teacher_id = %s AND te.week_number = %s -- ADD week_number filter
        ORDER BY ts.day_of_week, ts.period; -- Order by day/period within the selected week
        """
        # Pass the parameters in the correct order for the query
        cur.execute(query, (semester_id, teacher_id_from_user, week_number))

        fetched_entries = cur.fetchall()

        # --- Step 4: Convert datetime.time objects to strings and map day_of_week ---
        entries_for_json = []
        # Map DB day names (e.g., 'Monday') to frontend display names (e.g., '周一')
        # Adjust this map if your DB stores days differently
        day_map = {
             'Monday': '周一', 'Tuesday': '周二', 'Wednesday': '周三',
             'Thursday': '周四', 'Friday': '周五', 'Saturday': '周六', 'Sunday': '周日'
        }

        for row in fetched_entries:
            entry = dict(row)

            # Map day_of_week
            if 'day_of_week' in entry and entry['day_of_week'] in day_map:
                 entry['day_of_week'] = day_map[entry['day_of_week']]
            # Else: assume DB already stores '周一' etc. or frontend handles other formats

            # Format time fields
            if 'start_time' in entry and isinstance(entry['start_time'], datetime.time):
                entry['start_time'] = entry['start_time'].strftime('%H:%M:%S')
            # Ensure it's a string even if originally None/null from DB
            elif 'start_time' in entry and entry['start_time'] is None:
                 entry['start_time'] = None # Or empty string if preferred


            if 'end_time' in entry and isinstance(entry['end_time'], datetime.time):
                entry['end_time'] = entry['end_time'].strftime('%H:%M:%S')
            # Ensure it's a string even if originally None/null from DB
            elif 'end_time' in entry and entry['end_time'] is None:
                 entry['end_time'] = None # Or empty string if preferred


            # Handle potential None values from LEFT JOINs gracefully for frontend display
            if entry.get('major_name') is None:
                entry['major_name'] = '全校公共课' # Or another suitable indicator
            if entry.get('classroom_name') is None:
                entry['classroom_name'] = '待定' # Or another suitable indicator


            entries_for_json.append(entry)

        cur.close()

        return jsonify(entries_for_json), 200

    except psycopg2.Error as e:
        app.logger.error(f"API: DB error fetching teacher weekly timetable for user {user_id}, semester {semester_id}, week {week_number}: {e}",
                         exc_info=True)
        return jsonify({"message": "获取教师课表数据失败"}), 500
    except Exception as e:
        app.logger.error(
            f"API: An unexpected error occurred fetching teacher weekly timetable for user {user_id}, semester {semester_id}, week {week_number}: {e}",
            exc_info=True)
        return jsonify({"message": f"获取教师课表数据时发生内部错误"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()
@app.route('/api/time-slots', methods=['GET'])
def get_time_slots():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, day_of_week, period, start_time, end_time FROM time_slots ORDER BY day_of_week, period")
        time_slots = cur.fetchall()
        cur.close()

        # Format time objects for JSON
        formatted_time_slots = []
        for ts in time_slots:
            formatted_ts = dict(ts)
            if isinstance(formatted_ts.get('start_time'), datetime.time):
                 formatted_ts['start_time'] = formatted_ts['start_time'].strftime('%H:%M')
            if isinstance(formatted_ts.get('end_time'), datetime.time):
                 formatted_ts['end_time'] = formatted_ts['end_time'].strftime('%H:%M')
            formatted_time_slots.append(formatted_ts)


        return jsonify(formatted_time_slots)
    except Exception as e:
        app.logger.error(f"Error fetching time slots: {e}", exc_info=True)
        return jsonify({"message": "获取时间段信息失败"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


# API to submit teacher preference
@app.route('/api/teacher/scheduling-preferences', methods=['POST'])
# Assuming you have authentication/authorization middleware that provides user_id
# For simplicity, let's assume user_id is included in the request body for now,
# but ideally, it should come from the authenticated user session/token.
def submit_teacher_scheduling_preference():
    data = request.json

    # Validate required fields
    required_fields = ['user_id', 'semester_id', 'timeslot_id', 'preference_type', 'reason']
    for field in required_fields:
        if field not in data or data[field] is None:
            return jsonify({"error": f"缺少必填字段: {field}"}), 400

    user_id = data['user_id']
    semester_id = data['semester_id']
    timeslot_id = data['timeslot_id']
    preference_type = data['preference_type'] # Expecting 'avoid' for now
    reason = data['reason']

    if preference_type.lower() not in ['avoid', 'prefer']: # Basic validation for preference type
         return jsonify({"error": "无效的偏好类型"}), 400

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"message": "数据库连接失败"}), 500

        cur = conn.cursor()

        # 1. Verify user exists and is a teacher (Optional but good practice)
        cur.execute("SELECT id, role FROM users WHERE id = %s", (user_id,))
        user_info = cur.fetchone()
        if not user_info or user_info[1].lower() != 'teacher':
            conn.rollback()
            cur.close()
            return jsonify({"error": "用户不存在或不是教师类型"}), 403

        # 2. Get teacher_id from user_id
        cur.execute("SELECT id FROM teachers WHERE user_id = %s", (user_id,))
        teacher_profile = cur.fetchone()
        if not teacher_profile:
            conn.rollback()
            cur.close()
            return jsonify({"error": "找不到该用户关联的教师档案"}), 404
        teacher_id = teacher_profile[0]

        # 3. Verify semester and timeslot exist (Optional but good practice)
        cur.execute("SELECT 1 FROM semesters WHERE id = %s", (semester_id,))
        if not cur.fetchone():
            conn.rollback()
            cur.close()
            return jsonify({"error": "无效的学期ID"}), 400

        cur.execute("SELECT 1 FROM time_slots WHERE id = %s", (timeslot_id,))
        if not cur.fetchone():
            conn.rollback()
            cur.close()
            return jsonify({"error": "无效的时间段ID"}), 400


        # 4. Insert the preference into the database
        query = """
        INSERT INTO teacher_scheduling_preferences
        (teacher_id, semester_id, timeslot_id, preference_type, reason, status)
        VALUES (%s, %s, %s, %s, %s, 'pending')
        ON CONFLICT (teacher_id, semester_id, timeslot_id, preference_type)
        DO UPDATE SET
            reason = EXCLUDED.reason, -- Update reason if preference already exists
            status = 'pending', -- Reset status to pending on update
            updated_at = CURRENT_TIMESTAMP
        RETURNING id; -- Return the ID of the inserted/updated row
        """
        cur.execute(query, (teacher_id, semester_id, timeslot_id, preference_type.lower(), reason))

        preference_id = cur.fetchone()[0] # Get the returned ID

        conn.commit() # Commit the transaction
        cur.close()

        return jsonify({"message": "排课要求已成功提交", "id": preference_id}), 201 # 201 Created or 200 OK

    except psycopg2.IntegrityError as e:
        conn.rollback() # Rollback the transaction on integrity error
        app.logger.error(f"API: Integrity error submitting preference: {e}", exc_info=True)
        # This block might catch if FK constraints fail before the explicit checks,
        # or if the UNIQUE constraint is hit (though ON CONFLICT handles the unique case)
        return jsonify({"message": "数据完整性错误，请检查输入信息"}), 400 # More generic message

    except Exception as e:
        if conn: conn.rollback() # Ensure rollback on any other error
        app.logger.error(f"API: An unexpected error occurred submitting teacher preference: {e}", exc_info=True)
        return jsonify({"message": f"提交排课要求时发生内部错误"}), 500

    finally:
        if cur: cur.close()
        if conn: conn.close()

# Add this new route to your Flask application

@app.route('/api/teacher/<int:user_id>/scheduling-preferences', methods=['GET'])
# Assuming you have authentication/authorization middleware that verifies user_id
def get_teacher_scheduling_preferences(user_id):
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"message": "数据库连接失败"}), 500

        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Optional: Verify user exists and is a teacher (Good practice)
        cur.execute("SELECT id, role FROM users WHERE id = %s", (user_id,))
        user_info = cur.fetchone()
        if not user_info or user_info['role'].lower() != 'teacher':
            cur.close()
            return jsonify({"error": "用户不存在或不是教师类型"}), 403

        # Get teacher_id from user_id
        cur.execute("SELECT id FROM teachers WHERE user_id = %s", (user_id,))
        teacher_profile = cur.fetchone()
        if not teacher_profile:
            cur.close()
            return jsonify({"error": "找不到该用户关联的教师档案"}), 404
        teacher_id = teacher_profile['id']

        # Get optional semester_id from query parameters
        semester_id = request.args.get('semester_id', type=int)

        # Base query to fetch preferences
        query = """
        SELECT
            tsp.id,
            s.name as semester_name,
            ts.day_of_week,
            ts.period,
            ts.start_time,
            ts.end_time,
            tsp.preference_type,
            tsp.reason,
            tsp.status,
            tsp.created_at,
            tsp.updated_at
        FROM
            teacher_scheduling_preferences tsp
        JOIN
            semesters s ON tsp.semester_id = s.id
        JOIN
            time_slots ts ON tsp.timeslot_id = ts.id
        WHERE
            tsp.teacher_id = %s
        """
        query_params = [teacher_id]

        # Add semester filter if provided
        if semester_id is not None:
            query += " AND tsp.semester_id = %s"
            query_params.append(semester_id)
        query += " ORDER BY tsp.created_at DESC;" # Order by creation date, newest first
        cur.execute(query, query_params)
        fetched_preferences = cur.fetchall()
        # --- Format time objects and map status/type to Chinese ---
        preferences_for_json = []
        # Simple mappings (adjust if needed based on your stored values)
        status_map = {
            'pending': '待处理',
            'approved': '已批准',
            'rejected': '已拒绝',
            'applied': '已应用' # If your system tracks application in scheduling
            # Add other statuses if any
        }
        preference_type_map = {
             'avoid': '避免安排',
             'prefer': '优先安排'
         }
        day_map = { # Assuming DB stores English names
              'Monday': '周一', 'Tuesday': '周二', 'Wednesday': '周三',
              'Thursday': '周四', 'Friday': '周五', 'Saturday': '周六', 'Sunday': '周日'
        }


        for row in fetched_preferences:
            preference = dict(row)

            # Format time fields
            if 'start_time' in preference and isinstance(preference['start_time'], datetime.time):
                preference['start_time'] = preference['start_time'].strftime('%H:%M') # Using %H:%M for display
            if 'end_time' in preference and isinstance(preference['end_time'], datetime.time):
                preference['end_time'] = preference['end_time'].strftime('%H:%M') # Using %H:%M for display

            # Map status and type
            preference['status_display'] = status_map.get(preference.get('status', '').lower(), preference.get('status', '未知状态'))
            preference['preference_type_display'] = preference_type_map.get(preference.get('preference_type', '').lower(), preference.get('preference_type', '未知类型'))

            # Map day of week
            if 'day_of_week' in preference and preference['day_of_week'] in day_map:
                 preference['day_of_week_display'] = day_map[preference['day_of_week']]
            else:
                 preference['day_of_week_display'] = preference.get('day_of_week', '未知日期')


            # Format timestamps (optional, but good for history)
            if 'created_at' in preference and isinstance(preference['created_at'], datetime.datetime):
                 preference['created_at_formatted'] = preference['created_at'].strftime('%Y-%m-%d %H:%M')
            if 'updated_at' in preference and isinstance(preference['updated_at'], datetime.datetime):
                 preference['updated_at_formatted'] = preference['updated_at'].strftime('%Y-%m-%d %H:%M')


            preferences_for_json.append(preference)
        # --- End of Formatting ---


        cur.close()

        return jsonify(preferences_for_json), 200

    except Exception as e:
        app.logger.error(f"API: An unexpected error occurred fetching teacher preferences for user {user_id}: {e}", exc_info=True)
        return jsonify({"message": f"获取教师排课要求数据时发生内部错误"}), 500

    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route('/api/teacher/scheduling-preferences/<int:preference_id>', methods=['DELETE'])
def delete_teacher_scheduling_preference(preference_id):

    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None:
            return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor()

        user_id_from_frontend = request.args.get('user_id', type=int)
        if user_id_from_frontend is None:
             # Or get from session/token if available
             return jsonify({"message": "无法获取用户身份信息"}), 401 # Unauthorized

        # Get the actual teacher_id associated with the logged-in user_id
        cur.execute("SELECT id FROM teachers WHERE user_id = %s", (user_id_from_frontend,))
        teacher_profile = cur.fetchone()
        if not teacher_profile:
            cur.close()
            return jsonify({"error": "找不到该用户关联的教师档案或用户不是教师"}), 403 # Forbidden
        requester_teacher_id = teacher_profile[0]
        # --- END SECURE USER ID RETRIEVAL (Adapt this) ---


        # Check if the preference exists AND belongs to the requesting teacher
        query = """
        SELECT teacher_id FROM teacher_scheduling_preferences WHERE id = %s;
        """
        cur.execute(query, (preference_id,))
        preference_owner_info = cur.fetchone()

        if not preference_owner_info:
            # Preference with this ID does not exist
            cur.close()
            return jsonify({"error": "未找到要删除的排课要求。"}), 404

        preference_owner_teacher_id = preference_owner_info[0]

        # IMPORTANT SECURITY CHECK: Ensure the requesting teacher owns this preference
        if preference_owner_teacher_id != requester_teacher_id:
            cur.close()
            return jsonify({"error": "无权删除该排课要求。"}), 403 # Forbidden


        # If ownership is verified, proceed to delete
        delete_query = """
        DELETE FROM teacher_scheduling_preferences WHERE id = %s;
        """
        cur.execute(delete_query, (preference_id,))

        # Check if any row was actually deleted (should be 1 if found and owned)
        if cur.rowcount == 0:
             # This case should ideally not happen if the SELECT check passed,
             # but good to have for robustness. Could indicate a race condition or logic error.
             conn.rollback()
             cur.close()
             return jsonify({"error": "删除失败，可能要求已被移除或您无权操作。"}), 400


        conn.commit() # Commit the transaction
        cur.close()

        return jsonify({"message": "排课要求已成功删除"}), 200 # OK

    except Exception as e:
        if conn: conn.rollback() # Ensure rollback on any other error
        app.logger.error(f"API: An unexpected error occurred deleting preference {preference_id} for user {user_id_from_frontend}: {e}", exc_info=True)
        return jsonify({"message": f"删除排课要求时发生内部错误"}), 500

    finally:
        if cur: cur.close()
        if conn: conn.close()


#手动调课用
# --- 在 app.py 文件顶部添加必要的导入 ---
# (已有的导入...)
from flask import abort # 用于返回错误码

# --- Helper function for conflict checking (Simplified Example) ---
def check_conflict(conn, entry_id_to_update, new_timeslot_id, new_classroom_id, week_number):
    """
    检查更新后的条目是否与现有条目冲突 (简化版)。
    返回冲突描述字符串，如果无冲突则返回 None。
    注意：这个检查逻辑需要根据你的具体规则细化！
    """
    cur = None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 获取要更新的条目的基本信息 (教师, 专业, 学期)
        cur.execute("""
            SELECT teacher_id, major_id, semester_id
            FROM timetable_entries
            WHERE id = %s
        """, (entry_id_to_update,))
        entry_info = cur.fetchone()
        if not entry_info:
            return "要更新的条目不存在" # 或者在调用前检查

        teacher_id = entry_info['teacher_id']
        major_id = entry_info['major_id']
        semester_id = entry_info['semester_id'] # 用于限定范围

        # 检查教师冲突: 同学期、同周次、新时间段，是否有其他课 (排除自身)
        cur.execute("""
            SELECT te.id, c.name as course_name
            FROM timetable_entries te
            JOIN courses c ON te.course_id = c.id
            WHERE te.teacher_id = %s
              AND te.semester_id = %s
              AND te.week_number = %s
              AND te.timeslot_id = %s
              AND te.id != %s
        """, (teacher_id, semester_id, week_number, new_timeslot_id, entry_id_to_update))
        teacher_conflict = cur.fetchone()
        if teacher_conflict:
            return f"教师在该时间已有课程: {teacher_conflict['course_name']}"

        # 检查教室冲突: 同学期、同周次、新时间段、新教室，是否已被占用 (排除自身)
        if new_classroom_id: # 只有在指定了新教室时才检查
            cur.execute("""
                SELECT te.id, c.name as course_name, m.name as major_name
                FROM timetable_entries te
                JOIN courses c ON te.course_id = c.id
                JOIN majors m ON te.major_id = m.id
                WHERE te.classroom_id = %s
                  AND te.semester_id = %s
                  AND te.week_number = %s
                  AND te.timeslot_id = %s
                  AND te.id != %s
            """, (new_classroom_id, semester_id, week_number, new_timeslot_id, entry_id_to_update))
            classroom_conflict = cur.fetchone()
            if classroom_conflict:
                return f"教室在该时间已被专业 '{classroom_conflict['major_name']}' 的课程 '{classroom_conflict['course_name']}' 占用"

        # 检查专业/班级冲突: 同学期、同周次、新时间段，该专业是否已有其他课 (排除自身)
        cur.execute("""
            SELECT te.id, c.name as course_name
            FROM timetable_entries te
            JOIN courses c ON te.course_id = c.id
            WHERE te.major_id = %s
              AND te.semester_id = %s
              AND te.week_number = %s
              AND te.timeslot_id = %s
              AND te.id != %s
        """, (major_id, semester_id, week_number, new_timeslot_id, entry_id_to_update))
        major_conflict = cur.fetchone()
        if major_conflict:
            return f"该专业在该时间已有课程: {major_conflict['course_name']}"

        return None # 无冲突

    except Exception as e:
        app.logger.error(f"Conflict check error: {e}", exc_info=True)
        return f"冲突检查时发生错误: {e}" # 返回错误信息
    finally:
        if cur: cur.close()


# --- 添加新的 API 端点 ---

@app.route('/api/classrooms-list', methods=['GET'])
def get_classrooms_list():
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # 添加了 capacity 和 type 字段，前端可能需要
        cur.execute("SELECT id, building, room_number, capacity, room_type FROM classrooms ORDER BY building, room_number")
        classrooms = cur.fetchall()
        # 组合 building 和 room_number 为 name 方便显示
        for room in classrooms:
            room['name'] = f"{room['building']}-{room['room_number']}"
        return jsonify(classrooms), 200
    except Exception as e:
        app.logger.error(f"Error fetching classrooms list: {e}", exc_info=True)
        return jsonify({"message": "获取教室列表失败"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route('/api/timetables/entry/<int:entry_id>', methods=['PUT'])
def update_timetable_entry(entry_id):
    data = request.get_json()
    if not data:
        return jsonify({"message": "请求体不能为空"}), 400

    # --- 获取并验证输入 (修改部分) ---

    # 1. 获取 timeslot_id (期望是整数，如果不存在或无效则报错)
    raw_timeslot_id = data.get('timeslot_id')
    if raw_timeslot_id is None:  # 检查键是否存在
        # 根据你的业务逻辑，如果 timeslot_id 是必须的，则返回错误
        return jsonify({"message": "缺少必要参数: timeslot_id"}), 400
    try:
        new_timeslot_id = int(raw_timeslot_id)  # 尝试转换为整数
    except (ValueError, TypeError):
        # 值存在但无法转为整数
        return jsonify({"message": "timeslot_id 必须是一个有效的整数"}), 400

    # 2. 获取 classroom_id (期望是整数，但允许为 None/null)
    raw_classroom_id = data.get('classroom_id')  # 直接获取，允许 None
    new_classroom_id = None
    if raw_classroom_id is not None:  # 只有在不为 None 时才尝试转换
        try:
            new_classroom_id = int(raw_classroom_id)
        except (ValueError, TypeError):
            return jsonify({"message": "classroom_id 必须是一个有效的整数或 null"}), 400
    # 如果 raw_classroom_id 就是 None, new_classroom_id 保持为 None

    # 3. 获取 week_number (必须是正整数)
    raw_week_number = data.get('week_number')
    if raw_week_number is None:
        return jsonify({"message": "缺少必要参数: week_number"}), 400
    try:
        week_number = int(raw_week_number)
        if week_number <= 0:  # 添加业务逻辑验证
            raise ValueError("周数必须是正数")
    except (ValueError, TypeError):
        return jsonify({"message": "week_number 必须是一个有效的正整数"}), 400
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        conn.autocommit = False # 使用事务
        cur = conn.cursor()

        # --- 检查目标 timeslot 和 classroom 是否有效 (如果提供了 classroom) ---
        cur.execute("SELECT 1 FROM time_slots WHERE id = %s", (new_timeslot_id,))
        if not cur.fetchone():
            conn.rollback()
            return jsonify({"message": f"无效的时间段 ID: {new_timeslot_id}"}), 400
        if new_classroom_id is not None:
            cur.execute("SELECT 1 FROM classrooms WHERE id = %s", (new_classroom_id,))
            if not cur.fetchone():
                conn.rollback()
                return jsonify({"message": f"无效的教室 ID: {new_classroom_id}"}), 400

        # --- 执行冲突检查 ---
        # 注意：week_number 需要从 data 中获取，因为更新是针对特定周次的
        conflict_reason = check_conflict(conn, entry_id, new_timeslot_id, new_classroom_id, week_number)
        if conflict_reason:
            conn.rollback() # 回滚事务
            return jsonify({"message": f"无法更新，存在冲突: {conflict_reason}"}), 409 # 409 Conflict

        # --- 更新数据库 ---
        # 注意：这里只更新 timeslot_id 和 classroom_id
        # 如果需要更新其他字段（如 week_number），也需要加入 SET 子句
        # 但通常手动调整是移动到新的时间/地点，周次不变或由用户指定
        update_query = """
        UPDATE timetable_entries
        SET timeslot_id = %s, classroom_id = %s
        WHERE id = %s
        """
        # 使用 new_classroom_id，如果它是 None，数据库字段需要允许 NULL
        cur.execute(update_query, (new_timeslot_id, new_classroom_id, entry_id))

        if cur.rowcount == 0:
            conn.rollback()
            return jsonify({"message": "未找到要更新的课表条目，或数据未改变"}), 404

        conn.commit() # 提交事务
        return jsonify({"message": "课表条目更新成功"}), 200

    except psycopg2.Error as db_err:
        if conn: conn.rollback()
        app.logger.error(f"DB error updating timetable entry {entry_id}: {db_err}", exc_info=True)
        return jsonify({"message": f"数据库操作失败: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Error updating timetable entry {entry_id}: {e}", exc_info=True)
        return jsonify({"message": f"服务器内部错误: {e}"}), 500
    finally:
        if cur: cur.close()
        if conn:
            conn.autocommit = True # 恢复 autocommit 状态
            conn.close()

@app.route('/api/timetables/entry/<int:entry_id>', methods=['DELETE'])
def delete_timetable_entry(entry_id):
    conn = None
    cur = None
    try:
        conn = get_db_connection()
        if conn is None: return jsonify({"message": "数据库连接失败"}), 500
        cur = conn.cursor()
        conn.autocommit = True # 删除是单个操作

        cur.execute("DELETE FROM timetable_entries WHERE id = %s", (entry_id,))

        if cur.rowcount > 0:
            return jsonify({"message": f"课表条目 {entry_id} 删除成功"}), 200
        else:
            return jsonify({"message": "删除失败，课表条目可能不存在"}), 404

    except psycopg2.Error as db_err:
        app.logger.error(f"DB error deleting timetable entry {entry_id}: {db_err}", exc_info=True)
        return jsonify({"message": f"数据库操作失败: {db_err}"}), 500
    except Exception as e:
        app.logger.error(f"Error deleting timetable entry {entry_id}: {e}", exc_info=True)
        return jsonify({"message": f"服务器内部错误: {e}"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()

@app.route('/')
def index():
    return "Timetable Scheduling Backend API is running."


if __name__ == '__main__':
    app.run(debug=True, port=5000)
