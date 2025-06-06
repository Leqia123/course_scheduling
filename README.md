# 课程调度管理系统

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## 项目概述
* 一个基于Flask和Vue.js的全栈课程调度管理系统，包含教师、学生和管理员三种角色，提供课表生成、排课冲突检测、教学任务管理等功能。
* backend目录下app.py是后端总代码，scheduler_module.py是排课算法。
* course/src/views目录下是前端各界面代码，包括Login.vue（登录界面）、StudentDashboard.vue（学生登录后界面）、TeacherDashboard.vue（教师登录后界面）、AdminDashboard.vue（管理员登录后界面）、TimetableGridDisplay(studentdashboard用).vue用于显示课表。
* course/src/components目录下是各组件，其中有管理员界面的四个组件AdminImportCoursePlan.vue，AdminStudentTimetable.vue，AdminTeacherTimetable.vue，AdminManualScheduling.vue，分别代表课程计划管理界面、查询学生课表界面、查询教员课表界面、手动调整课表界面。还有教师界面的两个组件TeacherSchedulingRequest.vue、TeacherTimetable.vue，分别代表提出排课要求界面、查询教师课表界面。
* 
## 技术栈
### 后端 (backend)
- Python 3.9+
- Flask 2.0
- PostgreSQL
- SQLAlchemy
- psycopg2
- pandas

### 前端 (course)
- Vue.js 3
- Element Plus
- Axios
- Vue Router

### 数据库 (Database)
-PostgreSQL

## 功能模块
### 教师端
- 个人课表查询
- 排课时间偏好设置

### 学生端
- 实时课表查看
- 电子课表导出

### 管理员
- 教学计划导入（Excel）
- 手动排课调整
- 教师/学生课表管理
- 自动排课算法执行

## 安装步骤
### 后端依赖
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
