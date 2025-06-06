<template>
  <div class="page-content">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>我的课表</span>
        </div>
      </template>

      <!-- Controls for selecting Semester and Week -->
      <el-form :inline="true" class="controls-form">
        <el-form-item label="选择学期:">
          <el-select
            v-model="selectedSemesterId"
            placeholder="请选择学期"
            @change="onSemesterChange"
            clearable
            filterable
            style="width: 220px;"
          >
            <el-option
              v-for="semester in semesters"
              :key="semester.id"
              :label="semester.name"
              :value="semester.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="选择周次:">
          <el-select
            v-model="selectedWeek"
            placeholder="请选择周次"
            :disabled="!selectedSemesterId || weeks.length === 0"
            clearable
            style="width: 180px;"
          >
            <el-option
              v-for="week in weeks"
              :key="week"
              :label="`第 ${week} 周`"
              :value="week"
            />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            @click="fetchTeacherTimetable"
            :disabled="!selectedSemesterId || !selectedWeek"
            :loading="isLoading"
            :icon="Search"
          >
            查询课表
          </el-button>
        </el-form-item>
      </el-form>

      <!-- Status messages -->
      <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon @close="errorMessage=''" class="status-alert"/>
      <el-alert v-if="!loggedInUserId" title="未能获取您的教师信息（用户ID）。请联系管理员或重新登录。" type="error" :closable="false" show-icon class="status-alert"/>


      <!-- Timetable Display Area -->
      <div class="timetable-display-container" v-loading="isLoading">
        <div v-if="loggedInUserId">
          <div v-if="!isLoading && hasSearched && timetableEntries.length > 0" class="timetable-display-area">
              <!-- Pass fetched data to the grid display component -->
              <TimetableGridDisplay
                 :entries="timetableEntries"
                 :actualWeekNumber="Number(selectedWeek)"
                 :totalWeeks="selectedSemesterTotalWeeks"
                 viewType="teacher"
               />
          </div>
           <el-empty
               v-else-if="!isLoading && hasSearched && timetableEntries.length === 0"
               :description="`当前学期第 ${selectedWeek} 周没有您的课表信息`"
               class="empty-state"
           />
           <el-empty
               v-else-if="!hasSearched"
               description="请选择学期和周次后点击“查询课表”"
               class="empty-state"
           />
           <!-- Loading state is handled by v-loading -->
        </div>
         <!-- Error for missing loggedInUserId is handled by the alert above -->

      </div>

    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue';
import axios from 'axios';
import TimetableGridDisplay from './TimetableGridDisplay.vue'; // 引入课表展示组件
import {
    ElCard, ElForm, ElFormItem, ElSelect, ElOption, ElButton, ElAlert, ElEmpty, ElLoading, ElMessage
} from 'element-plus';
import { Search } from '@element-plus/icons-vue'; // Import Search icon

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

// Reactive state variables
const loggedInUserId = ref(null);
const semesters = ref([]);
const selectedSemesterId = ref(null); // Use null for better clearable behavior
const selectedSemesterTotalWeeks = ref(0);
const weeks = ref([]);
const selectedWeek = ref(null); // Use null for better clearable behavior
const timetableEntries = ref([]);
const isLoading = ref(false);
const errorMessage = ref('');
const hasSearched = ref(false); // To show initial/empty message correctly

// Fetch list of semesters from backend
const fetchSemesters = async () => {
  isLoading.value = true; // Consider loading state for initial semester fetch
  try {
    const response = await axios.get(`${API_BASE_URL}/api/semesters`);
    semesters.value = response.data;
    // Do not auto-select, let user choose.
    // if (semesters.value.length > 0) {
    //   selectedSemesterId.value = semesters.value[0].id;
    // }
  } catch (error) {
    console.error('Error fetching semesters:', error);
    errorMessage.value = `无法加载学期信息: ${error.response?.data?.message || error.message}`;
    // ElMessage.error(`无法加载学期信息: ${error.response?.data?.message || error.message}`);
  } finally {
      isLoading.value = false;
  }
};

// Fetch timetable data
const fetchTeacherTimetable = async () => {
  if (loggedInUserId.value === null) {
      // Already handled by the persistent alert, but double-check
      ElMessage.error('未能获取您的教师用户ID，无法查询课表。');
      return;
  }
  if (!selectedSemesterId.value || !selectedWeek.value) {
      ElMessage.warning('请先选择学期和周次。');
      return;
  }

  isLoading.value = true;
  errorMessage.value = ''; // Clear previous errors
  timetableEntries.value = []; // Clear previous timetable data
  hasSearched.value = true; // Mark that a search attempt has been made

  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/timetables/teacher-dashboard/${loggedInUserId.value}/semester/${selectedSemesterId.value}`,
      {
        params: {
          week: Number(selectedWeek.value) // Pass week as a query parameter
        }
      }
    );
    timetableEntries.value = response.data;
    console.log('Teacher Timetable fetched:', timetableEntries.value);
    // if (timetableEntries.value.length === 0) {
    //     // Optional: Show info message if data array is empty
    //     ElMessage.info(`第 ${selectedWeek.value} 周没有课表记录。`);
    // }

  } catch (error) {
    console.error('Error fetching teacher timetable:', error);
    timetableEntries.value = []; // Ensure array is empty on error
    if (error.response && error.response.status === 404) {
         // Backend specifically indicates no entries found
         // The el-empty state already handles this scenario based on timetableEntries.length
         //errorMessage.value = '该学期该周次没有找到您的课表信息。'; // Not needed if using el-empty
         console.log(`No timetable found for week ${selectedWeek.value}`);
     } else {
         // More general error
         const errorMsgText = error.response?.data?.message || error.response?.data?.error || error.message || '未知错误';
         errorMessage.value = `查询课表失败: ${errorMsgText}`;
         // ElMessage.error(`查询课表失败: ${errorMsgText}`); // Use alert for persistence
    }
  } finally {
    isLoading.value = false;
  }
};

// Handle semester selection change to populate weeks dropdown
const onSemesterChange = (newSemesterId) => {
  // Clear dependent state first
  weeks.value = [];
  selectedWeek.value = null;
  selectedSemesterTotalWeeks.value = 0;
  timetableEntries.value = []; // Clear timetable data
  hasSearched.value = false; // Reset search status
  errorMessage.value = ''; // Clear error message

  if (newSemesterId) {
      const semester = semesters.value.find(s => s.id === newSemesterId);
      if (semester) {
        selectedSemesterTotalWeeks.value = semester.total_weeks;
        weeks.value = Array.from({ length: semester.total_weeks }, (_, i) => i + 1);
      }
  }
};

// On component mount
onMounted(async () => {
   const storedUserId = localStorage.getItem('user_id');
   const storedUserRole = localStorage.getItem('userRole');

   if (storedUserId && storedUserRole && storedUserRole.toLowerCase() === 'teacher') {
       loggedInUserId.value = Number(storedUserId);
       console.log(`Teacher Timetable: User ID ${loggedInUserId.value} (Role: ${storedUserRole}) logged in.`);
       await fetchSemesters(); // Fetch semesters only if user is a valid teacher
   } else {
       // Error message is handled by the persistent el-alert bound to !loggedInUserId
       loggedInUserId.value = null;
       console.error('Teacher Timetable: Invalid or missing user ID/role in localStorage.');
       // No need to fetch semesters if user is invalid
   }
});

// Watcher is not strictly needed due to @change calling the handler
// watch(selectedSemesterId, (newId) => {
//     if (newId !== null) { // check for null if using clearable
//          onSemesterChange(newId);
//      } else {
//          // Handle case where semester is cleared
//          onSemesterChange(null);
//      }
// });

</script>

<style scoped>
.page-content {
  padding: 20px;
}
.card-header {
  font-size: 2em;
  font-weight: bold;
}

.controls-form {
  margin-bottom: 20px;
  /* Element Plus inline form handles spacing, but adjust if needed */
}
.controls-form .el-form-item {
    margin-bottom: 10px; /* Ensure consistent spacing */
}

.status-alert {
    margin-bottom: 20px;
}


.timetable-display-container {
    margin-top: 20px;
    min-height: 200px; /* Ensure container has height for v-loading and el-empty */
    position: relative; /* Needed for v-loading overlay */
}

.timetable-display-area {
  /* Optional styling for the area containing the grid itself */
  border: 1px solid #eee;
  padding: 5px; /* Minimal padding */
  background-color: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  border-radius: 4px;
}

.empty-state {
    /* Customize el-empty style if needed */
    padding: 40px 0; /* Add some padding */
}

</style>
