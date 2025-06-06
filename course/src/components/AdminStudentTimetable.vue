<template>
  <div class="timetable-view">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>查询专业课表</span>
        </div>
      </template>

      <!-- Controls Area -->
      <el-form :inline="true" class="controls-form">
        <el-form-item label="选择学期:">
          <el-select
            v-model="selectedSemesterId"
            placeholder="请选择学期"
            clearable
            filterable
            style="width: 240px;"
            @change="handleSemesterChange"
          >
            <el-option
              v-for="semester in semesters"
              :key="semester.id"
              :label="`${semester.name} ${semester.total_weeks ? `(共${semester.total_weeks}周)` : ''}`"
              :value="semester.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="选择专业:">
          <el-select
            v-model="selectedMajorId"
            placeholder="请选择专业"
            clearable
            filterable
            style="width: 150px;"
            :disabled="!selectedSemesterId"
            @change="handleMajorChange"
          >
            <el-option
              v-for="major in majors"
              :key="major.id"
              :label="major.name"
              :value="major.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="选择周数:">
          <el-select
            v-model="selectedWeek"
            placeholder="请选择周数"
            clearable
            style="width: 150px;"
            :disabled="!selectedSemesterId || availableWeeks.length === 0"
            @change="handleWeekChange"
          >
            <el-option
              v-for="week in availableWeeks"
              :key="week"
              :label="`第 ${week} 周`"
              :value="week.toString()"
              > <!-- 确保值为字符串，如果API需要字符串 -->
             </el-option>
             <!--  或者 :value="week" 如果API需要数字，并相应调整activeWeek的处理 -->
          </el-select>
        </el-form-item>

        <el-form-item >
          <el-button
            type="primary"
            @click="fetchMajorTimetable"
            :disabled="!selectedSemesterId || !selectedMajorId || !selectedWeek"
            :loading="isLoading"
            :icon="Search"
          >
            {{ isLoading ? '查询中...' : '查询课表' }}
          </el-button>
        </el-form-item>

        <el-form-item>
          <el-button
            type="success"
            @click="exportMajorTimetable"
            :disabled="!selectedSemesterId || !selectedMajorId"
            :loading="isLoadingExport"
            :icon="Download"
          >
            {{ isLoadingExport ? '导出中...' : '导出学期Excel' }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- Status Messages -->
      <el-alert v-if="errorMessage" :title="errorMessage" type="error" show-icon @close="errorMessage = ''" style="margin-top: 15px;"/>

      <!-- Timetable Display Area -->
      <div v-loading="isLoading" class="timetable-display-container">
        <div v-if="selectedSemesterId && selectedMajorId && selectedWeek">
          <div v-if="!isLoading && timetableEntries.length > 0" class="timetable-display-area">
            <TimetableGridDisplay
              :entries="timetableEntries"
              viewType="major"
              :totalWeeks="1"
              :currentWeek="Number(selectedWeek)"
              :targetMajorId="Number(selectedMajorId)"
            /> <!-- 传递当前周和专业ID给子组件 -->
          </div>
          <el-empty
              v-if="!isLoading && hasSearched && timetableEntries.length === 0 && !errorMessage"
              description="未查询到该专业在此学期、此周的排课数据。"
              style="margin-top: 20px;"
          />
        </div>
        <el-empty
            v-else-if="!selectedSemesterId || !selectedMajorId || !selectedWeek"
            description="请选择学期、专业和周数以查询课表"
            style="margin-top: 20px;"
        />
      </div>

    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import axios from 'axios';
import {
  ElCard, ElForm, ElFormItem, ElSelect, ElOption, ElButton, ElAlert, ElEmpty,
  ElLoading, ElMessage // ElMessage for transient feedback
} from 'element-plus';
import { Search, Download } from '@element-plus/icons-vue'; // Import icons
// Assume TimetableGridDisplay.vue is correctly imported
import TimetableGridDisplay from './TimetableGridDisplay.vue'; // Adjust path if necessary

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

// --- State ---
const semesters = ref([]);
const majors = ref([]);
const selectedSemesterId = ref(null); // Use null for better clearable behavior
const selectedMajorId = ref(null);    // Use null
const selectedWeek = ref(null);      // Use null, ensure value is string or number as API needs
const timetableEntries = ref([]);
const isLoading = ref(false);
const isLoadingExport = ref(false);
const errorMessage = ref('');
const hasSearched = ref(false); // Track if a search has been performed

// --- Computed Properties ---
// Selected semester data (ensure IDs are compared correctly, e.g., number vs string)
const selectedSemesterData = computed(() => {
    const idToFind = Number(selectedSemesterId.value); // Convert to number for comparison
    return semesters.value.find(s => s.id === idToFind);
});

// Available weeks based on selected semester
const availableWeeks = computed(() => {
  const total = selectedSemesterData.value?.total_weeks; // Already ensured to be number or 0
  if (total && total > 0) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  return [];
});

// --- Watchers ---
// Clear dependent selections and results when semester changes
watch(selectedSemesterId, (newVal) => {
    selectedMajorId.value = null;
    selectedWeek.value = null;
    clearTimetableAndStatus();
    // Automatically select first week if only one available? Optional UX enhancement
    // if (availableWeeks.value.length === 1) {
    //    selectedWeek.value = availableWeeks.value[0].toString();
    // }
});

// Clear week and results when major changes (optional, depends on desired UX)
watch(selectedMajorId, () => {
    // If you want changing major to force re-selecting week:
    selectedWeek.value = null;
    clearTimetableAndStatus();
    // If changing major should keep the week selection if valid, remove this watcher or comment out
});

// Clear results when week changes (typically desired)
watch(selectedWeek, () => {
    clearTimetableAndStatus(); // Clear previous results when week changes
});

// --- Lifecycle Hooks ---
onMounted(async () => {
  // Show loading indicator while fetching initial data
  const loadingInstance = ElLoading.service({ target: '.timetable-view', text: '加载基础数据...' });
  try {
      await Promise.all([fetchSemesters(), fetchMajors()]);
  } catch (e) {
       // Errors handled within functions using ElMessage
  } finally {
      loadingInstance.close();
  }
});

// --- Methods ---
// Fetch semesters list
const fetchSemesters = async () => {
  // isLoading.value = true; // Handled by overall loading instance on mount
  try {
    const response = await axios.get(`${API_BASE_URL}/api/semesters`);
    // Ensure total_weeks is a number
    semesters.value = response.data.map(s => ({
        ...s,
        total_weeks: (s.total_weeks !== undefined && s.total_weeks !== null) ? Number(s.total_weeks) : 0
    }));
  } catch (error) {
    ElMessage.error('获取学期列表失败。');
    console.error(error);
  } finally {
      // isLoading.value = false;
  }
};

// Fetch majors list
const fetchMajors = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/majors-list`);
    majors.value = response.data;
  } catch (error) {
    ElMessage.error('获取专业列表失败。');
    console.error(error);
  }
};

// Clear timetable data and status messages
const clearTimetableAndStatus = () => {
    timetableEntries.value = [];
    errorMessage.value = ''; // Clear persistent error message
    hasSearched.value = false; // Reset search status
};

// Handler functions (can be simplified if only clearing status)
const handleSemesterChange = () => {
    // Watcher handles clearing now
};

const handleMajorChange = () => {
    // Watcher handles clearing now
};

const handleWeekChange = () => {
    // Watcher handles clearing now
};

// Fetch timetable for the selected criteria
const fetchMajorTimetable = async () => {
  if (!selectedSemesterId.value || !selectedMajorId.value || !selectedWeek.value) {
      ElMessage.warning('请先选择学期、专业和周数。');
      return;
  }
  isLoading.value = true;
  errorMessage.value = ''; // Clear previous errors
  timetableEntries.value = [];
  hasSearched.value = true; // Mark that a search was attempted

  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/timetables/major/${selectedMajorId.value}/semester/${selectedSemesterId.value}`,
      {
        params: {
          // Ensure the 'week' param matches what the backend expects (string or number)
          week: selectedWeek.value
        }
      }
    );
    // Ensure response data is an array
    timetableEntries.value = Array.isArray(response.data) ? response.data : [];
    // Optional: Add logging for debugging
    console.log('MajorTimetable: Data received:', JSON.stringify(timetableEntries.value));
    if(timetableEntries.value.length === 0) {
        // No explicit message needed here, the el-empty will show
        console.log('MajorTimetable: Received empty array.');
    }
  } catch (error) {
    console.error('获取专业课表失败:', error);
    const message = error.response?.data?.message || error.message || '未知错误';
    errorMessage.value = `获取专业课表失败: ${message}`; // Show error in alert
    timetableEntries.value = []; // Ensure empty on error
  } finally {
    isLoading.value = false;
  }
};

// Export timetable to Excel (entire semester)
const exportMajorTimetable = async () => {
  if (!selectedSemesterId.value || !selectedMajorId.value) {
      ElMessage.warning('请先选择学期和专业以导出课表。');
      return;
  }
  isLoadingExport.value = true;
  errorMessage.value = ''; // Clear previous errors

  const loadingInstance = ElLoading.service({ text: '正在生成Excel文件...' });

  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/timetables/export/major/${selectedMajorId.value}/semester/${selectedSemesterId.value}`,
      { responseType: 'blob' } // Important for file download
    );

    // Create a download link
    const url = window.URL.createObjectURL(new Blob([response.data], { type: response.headers['content-type'] || 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }));
    const link = document.createElement('a');
    link.href = url;

    // Determine filename
    const contentDisposition = response.headers['content-disposition'];
    let fileName = `专业课表_(全学期).xlsx`; // Default
    const majorName = majors.value.find(m => m.id === Number(selectedMajorId.value))?.name;
    const semesterName = semesters.value.find(s => s.id === Number(selectedSemesterId.value))?.name;
    if (majorName && semesterName) {
        fileName = `专业课表_${majorName}_${semesterName}_(全学期).xlsx`;
    }
    if (contentDisposition) {
        const fileNameMatch = contentDisposition.match(/filename\*?=UTF-8''(.+)|filename="?(.+)"?/i);
        if (fileNameMatch && fileNameMatch.length > 1) {
            // Prioritize UTF-8 encoded filename if present
            fileName = decodeURIComponent(fileNameMatch[1] || fileNameMatch[2]);
        }
    }

    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click(); // Trigger download

    // Clean up
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    ElMessage.success('课表Excel文件已开始下载。');

  } catch (error) {
    console.error('导出Excel失败:', error);
     // Try to read error message from blob response if it's JSON
     let errorDetail = error.message || '未知错误';
     if (error.response && error.response.data instanceof Blob && error.response.data.type.includes('application/json')) {
         try {
             const errorJson = JSON.parse(await error.response.data.text());
             errorDetail = errorJson.message || errorDetail;
         } catch (parseError) {
             console.error("Failed to parse error blob:", parseError);
         }
     } else if (error.response?.data?.message) {
          errorDetail = error.response.data.message;
     }
    ElMessage.error(`导出Excel失败: ${errorDetail}`);
  } finally {
    isLoadingExport.value = false;
    loadingInstance.close();
  }
};
</script>

<style scoped>
.timetable-view {
  padding: 20px;
}
.card-header {
  font-size: 2em;
  font-weight: bold;
  justify-content: center;
  align-items: center;
  display: flex;
}

.controls-form {
  padding-bottom: 0px; /* Add some space below the form */
  /* Element Plus inline form handles spacing, adjust el-form-item margin if needed */
}

.controls-form .el-form-item {
   margin-bottom: 10px; /* Ensure vertical spacing when wrapped */
   margin-right: 15px; /* Space between items */
}
/* Last item no right margin */
.controls-form .el-form-item:last-child {
    margin-right: 0;
}


.timetable-display-container {
  margin-top: 20px;
  min-height: 200px; /* Give loading indicator some space */
}

.timetable-display-area {
  /* Add any specific styles for the grid container if needed */
}

/* Style el-empty if needed */
.el-empty {
    padding: 40px 0; /* Adjust padding */
}

/* Removed custom icon styles as Element Plus icons are used */
</style>
