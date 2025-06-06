<template>
  <div class="student-container timetable-view">
    <el-card shadow="never">
       <template #header>
        <div class="card-header">
          <span>学生个人课表</span>
           <!-- Display Welcome Message -->
          <span style="font-size: 0.9em; font-weight: normal; margin-left: auto; padding-right: 20px;">
            欢迎您，{{ loggedInUsername }}！
          </span>
           <el-button type="danger" :icon="SwitchButton" @click="logout" plain size="small">
              退出登录
           </el-button>
        </div>
      </template>

       <!-- Error if student info missing -->
       <el-alert
           v-if="!loggedInUserId && initialCheckDone"
           title="未能获取您的学生信息。请联系管理员或重新登录。"
           type="error"
           show-icon
           :closable="false"
           class="status-alert"
       />

      <!-- Timetable Query Controls -->
      <el-form :inline="true" class="controls-form" v-if="loggedInUserId">
         <!-- Semester Selection -->
         <el-form-item label="选择学期:">
            <el-select
              v-model="selectedSemesterId"
              placeholder="请选择学期"
              @change="onSemesterChange"
              clearable
              filterable
              style="width: 280px;"
            >
              <el-option
                v-for="semester in semesters"
                :key="semester.id"
                :label="`${semester.name} ${semester.total_weeks ? `(共${semester.total_weeks}周)` : ''}`"
                :value="semester.id"
              />
            </el-select>
         </el-form-item>

         <!-- Week Selection -->
         <el-form-item label="选择周次:">
            <el-select
              v-model="selectedWeek"
              placeholder="请选择周次"
              :disabled="!selectedSemesterId || availableWeeks.length === 0"
              @change="onWeekChange"
              clearable
              filterable
              style="width: 180px;"
            >
              <el-option
                v-for="week in availableWeeks"
                :key="week"
                :label="`第 ${week} 周`"
                :value="week"
              />
            </el-select>
         </el-form-item>

         <!-- Action Buttons -->
         <el-form-item>
            <el-button
                type="primary"
                @click="fetchStudentTimetable"
                :disabled="!selectedSemesterId || !selectedWeek"
                :loading="isLoading"
                :icon="Search"
            >
              {{ isLoading ? '查询中...' : '查询课表' }}
            </el-button>
            <el-button
                type="success"
                @click="exportStudentTimetable"
                :disabled="!selectedSemesterId"
                :loading="isLoadingExport"
                :icon="Download"
            >
              {{ isLoadingExport ? '导出中...' : '导出学期Excel' }}
            </el-button>
         </el-form-item>
      </el-form>

      <!-- Status Messages (Loading/Error for fetch) -->
      <!-- Using el-alert for feedback -->
      <el-alert v-if="isLoading" title="正在加载课表..." type="info" show-icon :closable="false" class="status-alert"/>
      <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon @close="errorMessage=''" class="status-alert"/>


      <!-- Timetable Display Area -->
       <div v-if="loggedInUserId && !isLoading && hasSearched" class="timetable-display-area">
          <!-- Use the existing TimetableGridDisplay component -->
          <TimetableGridDisplay
              v-if="timetableEntries.length > 0"
              :entries="timetableEntries"
              :totalWeeks="1"
              :actualWeekNumber="Number(selectedWeek)"
              viewType="student"
          />
           <!-- No data message -->
          <el-alert
              v-else-if="!errorMessage"
              :title="`未查询到您在此学期、第 ${selectedWeek} 周的排课数据。`"
              type="info"
              show-icon
              :closable="false"
              class="status-alert"
           />
           <!-- Note: errorMessage alert above handles the case where the fetch failed -->
       </div>
        <!-- Initial state message before searching -->
        <el-empty v-if="loggedInUserId && !hasSearched && !isLoading && !errorMessage" description="请选择学期和周次后点击查询" />

    </el-card>

    <!-- Logout button moved to card header -->
    <!--
    <el-button type="danger" @click="logout" style="margin-top: 20px;">
        退出登录
    </el-button>
    -->
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
// Import Element Plus components and utilities
import {
    ElCard, ElForm, ElFormItem, ElSelect, ElOption, ElButton, ElAlert, ElEmpty,
    ElMessage, ElMessageBox, ElLoading
} from 'element-plus';
// Import Element Plus icons
import { Search, Download, SwitchButton } from '@element-plus/icons-vue';

// Import the custom timetable display component
import TimetableGridDisplay from './TimetableGridDisplay(studentdashboard用).vue';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

const router = useRouter();

// --- State ---
const loggedInUsername = ref('');
const loggedInUserId = ref(null); // Store user_id from users table
const initialCheckDone = ref(false); // Flag to prevent showing initial error before check

const semesters = ref([]);
const selectedSemesterId = ref(null); // Use null for clearable el-select
const selectedWeek = ref(null); // Use null for clearable el-select
const timetableEntries = ref([]);

// --- Status Flags ---
const isLoading = ref(false); // Loading for fetching weekly timetable
const isLoadingExport = ref(false); // Loading for export
const errorMessage = ref('');
const hasSearched = ref(false); // Track if a search has been attempted

// --- Computed Properties ---
const selectedSemesterData = computed(() => {
    if (selectedSemesterId.value === null) return null;
    const idToFind = Number(selectedSemesterId.value);
    return semesters.value.find(s => s.id === idToFind);
});

const availableWeeks = computed(() => {
  const total = selectedSemesterData.value?.total_weeks;
  if (total && total > 0) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  return [];
});

// --- Watchers ---
watch(selectedSemesterId, (newVal, oldVal) => {
    if (newVal !== oldVal) {
        selectedWeek.value = null; // Clear week selection using null
        clearTimetableAndStatus();
        // Auto-select first week if semester is chosen and weeks exist
        if (newVal && availableWeeks.value.length > 0) {
            selectedWeek.value = 1;
            // Optionally trigger fetch automatically
            // nextTick(fetchStudentTimetable);
        }
    }
});

watch(selectedWeek, (newVal, oldVal) => {
    if (newVal !== oldVal && newVal !== null) {
        // Clear previous results when week changes, but don't reset hasSearched
        timetableEntries.value = [];
        errorMessage.value = '';
        // Optionally trigger fetch automatically
        // hasSearched.value = false; // Reset search status if auto-fetch is desired
        // nextTick(fetchStudentTimetable);
    } else if (newVal === null) {
        // Clear results if week is deselected
        clearTimetableAndStatus();
    }
});


// --- Lifecycle Hooks ---
onMounted(async () => {
  // Read user info from localStorage
  loggedInUsername.value = localStorage.getItem('username') || '学生用户';
  const storedUserId = localStorage.getItem('user_id');
  const storedUserRole = localStorage.getItem('userRole');

  if (storedUserId && storedUserRole && storedUserRole.toLowerCase() === 'student') {
      loggedInUserId.value = Number(storedUserId);
      console.log(`Student Dashboard: User ID ${loggedInUserId.value} (Role: ${storedUserRole}) logged in.`);
      // Fetch semesters only if loggedInUserId is valid
      await fetchSemesters();
      // Select first semester/week if available (optional)
      if (semesters.value.length > 0 && !selectedSemesterId.value) {
          selectedSemesterId.value = semesters.value[0].id;
          // Watcher will handle setting the first week if available
      }
  } else {
      errorMessage.value = '未获取到有效的学生登录信息。请尝试重新登录。';
      console.error('Student Dashboard: Invalid or missing user ID/role in localStorage.');
      // Optional: redirect
      // router.push('/login');
  }
  initialCheckDone.value = true; // Mark that the initial user check is complete
});

// --- Methods ---

// Fetch semesters
const fetchSemesters = async () => {
  const loadingInstance = ElLoading.service({ text: '加载学期列表...' });
  try {
    const response = await axios.get(`${API_BASE_URL}/api/semesters`);
    semesters.value = response.data.map(s => ({
        ...s,
        id: Number(s.id),
        total_weeks: Number(s.total_weeks) || 0
    }));
    errorMessage.value = '';
  } catch (error) {
    errorMessage.value = '获取学期列表失败。';
    console.error('Error fetching semesters:', error);
    // ElMessage.error('获取学期列表失败。'); // Alternative feedback
  } finally {
      loadingInstance.close();
  }
};

// Clear timetable data and status messages
const clearTimetableAndStatus = () => {
    timetableEntries.value = [];
    errorMessage.value = '';
    hasSearched.value = false; // Reset search status
};

// Handle selection changes (mostly handled by watchers now)
const onSemesterChange = () => { /* Watcher handles logic */ };
const onWeekChange = () => { /* Watcher handles logic */ };

// Fetch student timetable for the selected week
const fetchStudentTimetable = async () => {
  if (loggedInUserId.value === null || selectedSemesterId.value === null || selectedWeek.value === null) {
      ElMessage.warning('请先选择学期和周次。');
      return;
  }

  isLoading.value = true;
  errorMessage.value = '';
  timetableEntries.value = []; // Clear old data before fetch
  hasSearched.value = true; // Mark that a search was attempted

  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/timetables/student/${loggedInUserId.value}/semester/${selectedSemesterId.value}`,
      { params: { week: Number(selectedWeek.value) } }
    );

    timetableEntries.value = Array.isArray(response.data) ? response.data : [];
    console.log(`Student Dashboard: Fetched ${timetableEntries.value.length} entries for week ${selectedWeek.value}.`);

     if (timetableEntries.value.length === 0) {
       // No need for a separate message here, the v-else-if in template handles it
     }

  } catch (error) {
    if (error.response && error.response.status === 404) {
        errorMessage.value = error.response.data.message || '未找到您的学生信息或专业关联，无法获取课表。';
    } else {
        errorMessage.value = `获取个人课表失败: ${error.response?.data?.message || error.message}`;
    }
    timetableEntries.value = []; // Ensure clear on error
    console.error('Error fetching student timetable:', error);
  } finally {
    isLoading.value = false;
  }
};

// Export student timetable for the entire selected semester
const exportStudentTimetable = async () => {
  if (loggedInUserId.value === null || selectedSemesterId.value === null) {
       ElMessage.warning('请先选择学期。');
       return;
  }

  isLoadingExport.value = true;
  errorMessage.value = ''; // Clear previous error message shown in alert

  const loadingInstance = ElLoading.service({ text: '正在生成并导出Excel文件...' });

  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/timetables/export/student/${loggedInUserId.value}/semester/${selectedSemesterId.value}`,
      { responseType: 'blob' }
    );

    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;

    // Try to get filename from header, otherwise construct one
    let filename = `我的课表_${loggedInUsername.value}_学期${selectedSemesterId.value}.xlsx`; // Default
    const contentDisposition = response.headers['content-disposition'];
     if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename\*?=(UTF-8''|")?([^";]+)/i);
        if (filenameMatch && filenameMatch[2]) {
            filename = decodeURIComponent(filenameMatch[2].replace(/["']/g, '')); // Decode and remove quotes
        } else {
             const fallbackMatch = contentDisposition.match(/filename="?(.+)"?/i);
              if (fallbackMatch && fallbackMatch[1]) filename = fallbackMatch[1];
        }
    }
    // Fallback if header parsing fails, use a more descriptive name
    if (filename.startsWith('我的课表_') && filename.includes(`学期${selectedSemesterId.value}`)) {
         const semesterName = semesters.value.find(s => s.id === Number(selectedSemesterId.value))?.name || `Semester_${selectedSemesterId.value}`;
         filename = `我的课表_${loggedInUsername.value}_${semesterName}_(全学期).xlsx`;
    }


    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    ElMessage.success('课表Excel文件已开始下载。');

  } catch (error) {
    let errorMsg = '导出Excel失败。';
    if (error.response) {
        // Try to read error message from blob response if it's JSON
        if (error.response.data instanceof Blob && error.response.data.type === "application/json") {
            try {
                const errJson = JSON.parse(await error.response.data.text());
                errorMsg = `导出Excel失败: ${errJson.message || '未知错误'}`;
            } catch (parseError) {
                 errorMsg = `导出Excel失败: ${error.response.statusText || '未知错误'}`;
            }
        } else if (error.response.data?.message) {
            errorMsg = `导出Excel失败: ${error.response.data.message}`;
        } else if (error.response.status === 404) {
           errorMsg = '未找到该学期的个人排课数据可供导出。';
        } else {
           errorMsg = `导出Excel失败: ${error.message}`;
        }
    } else {
        errorMsg = `导出Excel失败: ${error.message}`;
    }
    errorMessage.value = errorMsg; // Show error in the alert
    console.error('Error exporting student timetable:', error);
  } finally {
    isLoadingExport.value = false;
    loadingInstance.close();
  }
};


// Logout
const logout = async () => {
    try {
        await ElMessageBox.confirm(
            '您确定要退出登录吗?',
            '确认退出',
            {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning',
            }
        );
        // User confirmed
        localStorage.removeItem('token');
        localStorage.removeItem('userRole');
        localStorage.removeItem('username');
        localStorage.removeItem('user_id');
        ElMessage.success('已退出登录');
        router.push('/login');
    } catch (action) {
        // User clicked cancel or closed the box
        if (action === 'cancel') {
            // ElMessage.info('已取消退出'); // Optional feedback
        }
    }
};

</script>

<style scoped>
.student-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 2em;
  font-weight: bold;
}

.controls-form {
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 20px;
}

/* Adjust spacing for inline form items */
.controls-form .el-form-item {
  margin-bottom: 5px; /* Reduce bottom margin */
  margin-right: 15px;
}

.status-alert {
  margin-top: 15px;
  margin-bottom: 15px;
}

.timetable-display-area {
  margin-top: 20px;
}

/* Ensure ElEmpty takes up space */
.el-empty {
    margin-top: 30px;
}
</style>
