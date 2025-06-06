<template>
  <div class="page-content">
    <h2>手动调整课表</h2>

    <!-- 1. 学期选择 -->
    <el-select v-model="selectedSemester" placeholder="请选择学期" @change="handleSemesterChange" filterable style="margin-right: 10px;">
      <el-option
        v-for="semester in semesters"
        :key="semester.id"
        :label="semester.name"
        :value="semester.id">
      </el-option>
    </el-select>

    <!-- 2. 周次选择 -->
    <el-select v-model="selectedWeek" placeholder="请选择周次" v-if="selectedSemester && semesterWeeks > 0" filterable>
       <el-option
         v-for="week in availableWeeks"
         :key="week"
         :label="`第 ${week} 周`"
         :value="week">
       </el-option>
    </el-select>

    <el-divider></el-divider>

    <!-- 3. 课表网格 -->
    <div v-if="selectedSemester && selectedWeek && !loading && semesterWeeks > 0">
        <el-table :data="periods" border style="width: 100%" v-loading="loading">
            <el-table-column prop="timeLabel" label="时间" width="120"  align="center">
                <template #default="scope">
                    <div v-html="scope.row.timeLabel.replace('\\n', '<br/>')"></div>
                </template>
            </el-table-column>
            <el-table-column v-for="day in daysOfWeek" :key="day.value" :label="day.label" align="center">
                <template #default="scope">
                    <div class="timetable-cell" @click="handleCellClick(scope.row.period, day.value, selectedWeek)">
                        <div v-for="entry in getEntriesForCell(selectedWeek, day.value, scope.row.period)" :key="entry.id" class="timetable-entry" @click.stop="openEditModal(entry)">
                            <el-tooltip effect="dark" placement="top">
                                <template #content>
                                    课程: {{ entry.course_name }} ({{ entry.course_type }})<br/>
                                    教师: {{ entry.teacher_name }}<br/>
                                    专业: {{ entry.major_name }}<br/>
                                    教室: {{ entry.classroom_name || '未指定' }}<br/>
                                    周次: {{ entry.week_number }}<br/>
                                    点击编辑
                                </template>
                                <div>
                                    <p><strong>{{ entry.course_name }}</strong></p>
                                    <p><small>{{ entry.teacher_name }}</small></p>
                                    <p><small>{{ entry.classroom_name || 'N/A' }}</small></p>
                                </div>
                            </el-tooltip>
                        </div>
                        <div v-if="getEntriesForCell(selectedWeek, day.value, scope.row.period).length === 0" class="empty-cell">

                        </div>
                    </div>
                </template>
            </el-table-column>
        </el-table>
    </div>
    <el-alert v-else-if="selectedSemester && !loading && semesterWeeks <= 0" title="请先为该学期设置有效的起止日期以计算周数" type="warning" show-icon></el-alert>
    <el-empty v-else-if="!selectedSemester && !loading" description="请先选择一个学期"></el-empty>
    <el-skeleton :rows="10" animated v-if="loading" />


    <!-- 4. 编辑/添加课表项的对话框 (保持不变) -->
    <el-dialog v-model="editModalVisible" :title="modalTitle" width="500px" @close="resetEditForm">
      <el-form :model="editForm" ref="editFormRef" label-width="100px">
        <!-- 表单内容不变 -->
        <el-form-item label="课程">
          <el-input :value="editForm.course_name" disabled></el-input>
        </el-form-item>
         <el-form-item label="教师">
           <el-input :value="editForm.teacher_name" disabled></el-input>
         </el-form-item>
        <el-form-item label="专业">
          <el-input :value="editForm.major_name" disabled></el-input>
        </el-form-item>
        <el-form-item label="周次">
           <el-input :value="editForm.week_number" disabled></el-input>
        </el-form-item>
        <el-form-item label="时间段" prop="timeslot_id" :rules="[{ required: true, message: '请选择时间段', trigger: 'change' }]">
          <el-select v-model="editForm.timeslot_id" placeholder="请选择新的时间段" filterable>
            <el-option
              v-for="slot in timeSlots"
              :key="slot.id"
              :label="`${dayMap[slot.day_of_week] || slot.day_of_week} 第${slot.period}节 (${slot.start_time}-${slot.end_time})`"
              :value="slot.id">
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="教室" prop="classroom_id">
          <el-select v-model="editForm.classroom_id" placeholder="请选择新的教室" clearable filterable>
             <el-option
               v-for="room in classrooms"
               :key="room.id"
               :label="`${room.name} (${room.type || '未知类型'}, 容纳 ${room.capacity || 'N/A'})`"
               :value="room.id">
             </el-option>
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
           <el-button type="danger" @click="handleDeleteEntry" :loading="deleting">删除此安排</el-button>
           <el-button @click="editModalVisible = false">取消</el-button>
           <el-button type="primary" @click="saveTimetableEntry" :loading="saving">保存更改</el-button>
        </span>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import axios from 'axios';
import { ElMessage, ElMessageBox } from 'element-plus';

const API_BASE_URL = 'http://localhost:5000';

// --- 响应式状态 ---
const semesters = ref([]);
const selectedSemester = ref(null);
const semesterWeeks = ref(0); // 总周数
const selectedWeek = ref(null); // 新增：当前选中的周次 (可以是 null 或 number)
const timetableData = ref([]);
const timeSlots = ref([]);
const classrooms = ref([]);
const loading = ref(false);
// const loadingWeekData = ref(false); // 不再需要按周加载状态，统一用 loading
const editModalVisible = ref(false);
const editForm = ref({});
const editFormRef = ref(null);
const isEditMode = ref(true);
const saving = ref(false);
const deleting = ref(false);
// const activeWeek = ref('1'); // 移除 activeWeek

const daysOfWeek = ref([ // 保持不变
  { label: '周一', value: '周一' },
  { label: '周二', value: '周二' },
  { label: '周三', value: '周三' },
  { label: '周四', value: '周四' },
  { label: '周五', value: '周五' },

]);

const dayMap = { // 保持不变
  'Monday': '周一', 'Tuesday': '周二', 'Wednesday': '周三',
  'Thursday': '周四', 'Friday': '周五', 'Saturday': '周六', 'Sunday': '周日'
};

// --- 计算属性 ---
const modalTitle = computed(() => isEditMode.value ? '编辑课表条目' : '添加课表条目');

// 计算可供选择的周次列表 (1 到 semesterWeeks)
const availableWeeks = computed(() => {
    if (semesterWeeks.value <= 0) {
        return [];
    }
    return Array.from({ length: semesterWeeks.value }, (_, i) => i + 1);
});


const periods = computed(() => { // 保持不变
    const uniquePeriods = new Map();
    timeSlots.value.forEach(slot => {
        if (!uniquePeriods.has(slot.period)) {
            const startTime = slot.start_time ? slot.start_time.substring(0, 5) : '';
            const endTime = slot.end_time ? slot.end_time.substring(0, 5) : '';
            uniquePeriods.set(slot.period, {
                period: slot.period,
                timeLabel: `第${slot.period}节\n${startTime}-${endTime}`
            });
        }
    });
    return Array.from(uniquePeriods.values()).sort((a, b) => a.period - b.period);
});

// getWeekTimetable 函数不再需要，el-table 的 :data 直接绑定 periods

// 获取特定单元格的排课条目 (修改：第一个参数是选中的周次)
const getEntriesForCell = (week, dayValue, period) => {
    // 确保 week 是数字类型进行比较
    const weekNum = typeof week === 'string' ? parseInt(week, 10) : week;
    // 如果 week 是 null 或者 NaN (比如刚选学期还没选周)，返回空数组
    if (weekNum === null || isNaN(weekNum)) {
        return [];
    }

    return timetableData.value.filter(entry =>
        entry.week_number === weekNum && // 使用转换后的数字比较
        entry.day_of_week === dayValue &&
        entry.period === period
    );
};

// --- 方法 ---
const fetchSemesters = async () => { // 保持不变
  loading.value = true;
  try {
    const response = await axios.get(`${API_BASE_URL}/api/semesters`);
    semesters.value = response.data;
  } catch (error) {
    console.error("获取学期列表失败:", error);
    ElMessage.error('获取学期列表失败');
  } finally {
    loading.value = false;
  }
};

const fetchTimeSlots = async () => { // 保持不变
    try {
        const response = await axios.get(`${API_BASE_URL}/api/time-slots`);
        timeSlots.value = response.data.map(slot => ({
             ...slot,
             start_time: slot.start_time || '',
             end_time: slot.end_time || ''
         }));
    } catch (error) {
        console.error("获取时间段失败:", error);
        ElMessage.error('获取时间段信息失败');
    }
};

const fetchClassrooms = async () => { // 保持不变
    try {
        const response = await axios.get(`${API_BASE_URL}/api/classrooms-list`);
        classrooms.value = response.data;
    } catch (error) {
        console.error("获取教室列表失败:", error);
        ElMessage.error('获取教室列表失败');
    }
};

// 修改：处理学期改变的事件
const handleSemesterChange = (newSemesterId) => {
    selectedWeek.value = null; // 重置选中的周次
    semesterWeeks.value = 0; // 重置总周数
    timetableData.value = []; // 清空课表数据
    if (newSemesterId) {
        loadTimetableData(); // 加载新学期数据
    }
};

// 加载选定学期的课表数据和相关信息
const loadTimetableData = async () => {
  if (!selectedSemester.value) return;
  loading.value = true;
  timetableData.value = []; // 清空旧数据

  // 获取当前学期的周数
  const currentSemester = semesters.value.find(s => s.id === selectedSemester.value);
  semesterWeeks.value = currentSemester ? (currentSemester.total_weeks || 0) : 0;

  if (semesterWeeks.value > 0) {
      // 设置默认选中第一周
      selectedWeek.value = 1;
  } else {
       selectedWeek.value = null; // 没有周数，不能选周
       ElMessage.warning('当前学期未设置有效起止日期，无法显示周课表。');
       loading.value = false;
       return;
  }

  try {
    // 获取时间段和教室列表 (可以在 fetchSemesters 后就获取一次，不必每次都获取)
    // 这里假设 timeSlots 和 classrooms 已经或将会被加载
    if (timeSlots.value.length === 0) await fetchTimeSlots();
    if (classrooms.value.length === 0) await fetchClassrooms();

    // 获取完整学期课表数据
    const response = await axios.get(`${API_BASE_URL}/api/timetables/semester/${selectedSemester.value}`);

    // 合并时间段信息 (保持不变)
    const timeSlotMap = new Map(timeSlots.value.map(slot => [slot.id, slot]));
    timetableData.value = response.data.map(entry => {
        const slotInfo = timeSlotMap.get(entry.timeslot_id);
        return {
            ...entry,
            day_of_week: slotInfo ? slotInfo.day_of_week : null,
            period: slotInfo ? slotInfo.period : null,
            start_time: slotInfo ? (slotInfo.start_time || '') : '',
            end_time: slotInfo ? (slotInfo.end_time || '') : '',
        };
    });

  } catch (error) {
    console.error("加载课表数据失败:", error);
    ElMessage.error(`加载学期 ${selectedSemester.value} 的课表数据失败`);
    timetableData.value = [];
  } finally {
    loading.value = false;
  }
};

// handleWeekChange 方法不再需要

const handleCellClick = (period, dayValue, week) => { // week 参数现在是 selectedWeek
    console.log(`Clicked cell: Week ${week}, Day ${dayValue}, Period ${period}`);
};

const openEditModal = (entry) => { // 保持不变
  isEditMode.value = true;
  editForm.value = JSON.parse(JSON.stringify(entry));
  editForm.value.timeslot_id = entry.timeslot_id ? parseInt(entry.timeslot_id, 10) : null;
  editForm.value.classroom_id = entry.classroom_id ? parseInt(entry.classroom_id, 10) : null;
  editModalVisible.value = true;
};

const resetEditForm = () => { // 保持不变
  editForm.value = {};
};

const saveTimetableEntry = async () => { // 保持不变，但完成后需要刷新当前周
  if (!editFormRef.value) return;
  await editFormRef.value.validate(async (valid) => {
    if (valid) {
      saving.value = true;
      try {
        const entryId = editForm.value.id;
        const payload = {
          timeslot_id: editForm.value.timeslot_id,
          classroom_id: editForm.value.classroom_id,
          week_number: editForm.value.week_number
        };
        await axios.put(`${API_BASE_URL}/api/timetables/entry/${entryId}`, payload);
        ElMessage.success('课表条目更新成功');
        editModalVisible.value = false;
        // 重新加载整个学期数据以确保一致性
        await loadTimetableData();
      } catch (error) {
        console.error("更新课表条目失败:", error);
        const errorMsg = error.response?.data?.message || '更新失败';
        ElMessage.error(errorMsg);
      } finally {
        saving.value = false;
      }
    } else {
      console.log('表单验证失败');
      return false;
    }
  });
};

const handleDeleteEntry = async () => { // 保持不变，但完成后需要刷新当前周
  if (!editForm.value || !editForm.value.id) return;
  try {
      await ElMessageBox.confirm(
        `确定要删除课程 "${editForm.value.course_name}" 在第 ${editForm.value.week_number} 周的这个安排吗？此操作不可恢复。`,
        '确认删除',
        { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' }
      );
      deleting.value = true;
      const entryId = editForm.value.id;
      try {
        await axios.delete(`${API_BASE_URL}/api/timetables/entry/${entryId}`);
        ElMessage.success('课表条目删除成功');
        editModalVisible.value = false;
        // 重新加载整个学期数据
        await loadTimetableData();
      } catch (error) {
        console.error("删除课表条目失败:", error);
        const errorMsg = error.response?.data?.message || '删除失败';
        ElMessage.error(errorMsg);
      } finally {
        deleting.value = false;
      }
  } catch (action) {
      if (action === 'cancel') ElMessage.info('已取消删除');
  }
};

// --- 生命周期钩子 ---
onMounted(() => {
  fetchSemesters(); // 获取学期
  // 可以在这里就获取时间段和教室列表，避免每次换学期都请求
  fetchTimeSlots();
  fetchClassrooms();
});

// 监视选中学期变化 (现在通过 @change 事件处理)
// watch(selectedSemester, ...) 移除

// 监视选中的周次变化 (可选，如果切换周需要特殊处理时使用)
// watch(selectedWeek, (newWeek) => {
//   if (newWeek !== null) {
//     console.log(`Selected week changed to: ${newWeek}`);
//     // 如果需要按周加载数据，可以在这里触发
//   }
// });

</script>

<style scoped> /* 样式可以保持不变 */
.page-content {
  padding: 20px;
  font-size: 22px;
  text-align: center;
}
.el-select {
  margin-bottom: 20px;
  min-width: 200px; /* 可以调整宽度 */
}

.timetable-cell {
  min-height: 180px;

  padding: 5px;
  position: relative;
  cursor: pointer;
  border: 1px dashed #eee;

  flex-direction: column;
  align-items: center;
  justify-content: flex-start; /* 让内容从顶部开始排列 */
  overflow-y: auto; /* 如果内容过多允许滚动 */
  max-height: 250px; /* 限制最大高度，防止单元格过高 */
}
.timetable-cell:hover {
    background-color: #f5f7fa;
}
.timetable-entry {
  background-color: #ecf5ff;
  border: 1px solid #b3d8ff;
  border-radius: 4px;
  padding: 5px;
  margin-bottom: 3px;
  font-size: 14px;
  width: 95%;
  text-align: center;
  cursor: pointer;
  transition: background-color 0.2s;
}
.timetable-entry:hover {
  background-color: #d9ecff;
}
.timetable-entry p {
    margin: 2px 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.dialog-footer {
    display: flex;
    justify-content: space-between;
    width: 100%;
}
.el-table .cell {
    padding: 5px;

}
.el-table th .cell, .el-table td .cell {
    white-space: pre-wrap;
    line-height: 1.4;

}
</style>
